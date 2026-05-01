import logging
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import HTTPException

from app.db import get_supabase_client
from app.models.enums import LogAction, LogStatus
from app.models.schemas import ScheduleCreate, ScheduleResponse
from app.services import vm_service

_scheduler: BackgroundScheduler | None = None

log = logging.getLogger("NexVM.scheduler")


def _parse_cron(expr: str) -> dict:
    parts = expr.strip().split()
    if len(parts) < 5:
        raise ValueError(f"Invalid cron expression: {expr}")
    return {
        "minute": parts[0],
        "hour": parts[1],
        "day": parts[2],
        "month": parts[3],
        "day_of_week": parts[4],
    }


def _execute_scheduled_action(schedule_id: str, vm_id: str, action: str, user_id: str) -> None:
    try:
        if action == "start":
            vm_service.start_vm(vm_id, user_id=None, actor_id=user_id)
        elif action == "stop":
            vm_service.stop_vm(vm_id, user_id=None, actor_id=user_id)
        else:
            return

        supabase = get_supabase_client()
        now = datetime.now(timezone.utc).isoformat()
        supabase.table("vm_schedules").update({"last_run": now}).eq("id", schedule_id).execute()

        log.info("Scheduled %s executed for VM %s (schedule %s)", action, vm_id, schedule_id)
    except Exception as exc:
        log.warning("Scheduled %s failed for VM %s: %s", action, vm_id, exc)


def start_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        return

    _scheduler = BackgroundScheduler(daemon=True)
    _scheduler.start()
    log.info("APScheduler started")

    _load_existing_schedules()


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None


def _load_existing_schedules() -> None:
    try:
        supabase = get_supabase_client()
        if supabase is None:
            log.warning("Supabase client not ready — skipping schedule load")
            return
        result = supabase.table("vm_schedules").select("*").eq("enabled", True).execute()
        for row in result.data or []:
            _add_job(row["id"], row["vm_id"], row["action"], row["cron_expr"], row["user_id"])
        log.info("Loaded %d schedules", len(result.data or []))
    except Exception as exc:
        log.warning("Failed to load existing schedules (table may not exist yet): %s", exc)


def _add_job(schedule_id: str, vm_id: str, action: str, cron_expr: str, user_id: str) -> None:
    if _scheduler is None:
        return
    try:
        cron_fields = _parse_cron(cron_expr)
        trigger = CronTrigger(**cron_fields)
        _scheduler.add_job(
            _execute_scheduled_action,
            trigger=trigger,
            id=schedule_id,
            args=[schedule_id, str(vm_id), action, str(user_id)],
            replace_existing=True,
        )
    except Exception as exc:
        log.warning("Failed to add job %s: %s", schedule_id, exc)


def _remove_job(schedule_id: str) -> None:
    if _scheduler is None:
        return
    try:
        _scheduler.remove_job(schedule_id)
    except Exception:
        pass


def list_schedules(user_id: str) -> list[ScheduleResponse]:
    supabase = get_supabase_client()
    result = (
        supabase.table("vm_schedules")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )
    return [ScheduleResponse(**row) for row in result.data]


def list_schedules_for_vm(vm_id: str, user_id: str) -> list[ScheduleResponse]:
    supabase = get_supabase_client()
    result = (
        supabase.table("vm_schedules")
        .select("*")
        .eq("user_id", user_id)
        .eq("vm_id", vm_id)
        .order("created_at", desc=True)
        .execute()
    )
    return [ScheduleResponse(**row) for row in result.data]


def create_schedule(data: ScheduleCreate, user_id: str) -> ScheduleResponse:
    vm_service._get_vm_or_404(str(data.vm_id), user_id)

    supabase = get_supabase_client()
    inserted = (
        supabase.table("vm_schedules")
        .insert({
            "user_id": user_id,
            "vm_id": str(data.vm_id),
            "action": data.action,
            "cron_expr": data.cron_expr,
            "enabled": True,
        })
        .execute()
    )

    row = inserted.data[0]

    _add_job(row["id"], row["vm_id"], row["action"], row["cron_expr"], row["user_id"])

    try:
        supabase.table("logs").insert({
            "user_id": user_id,
            "action": LogAction.schedule_vm,
            "target": str(data.vm_id),
            "status": LogStatus.success,
            "message": f"Schedule created: {data.action} ({data.cron_expr})",
        }).execute()
    except Exception:
        pass

    return ScheduleResponse(**row)


def delete_schedule(schedule_id: str, user_id: str) -> None:
    supabase = get_supabase_client()
    result = (
        supabase.table("vm_schedules")
        .select("*")
        .eq("id", schedule_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Schedule not found")

    _remove_job(schedule_id)
    supabase.table("vm_schedules").delete().eq("id", schedule_id).execute()

    try:
        supabase.table("logs").insert({
            "user_id": user_id,
            "action": LogAction.schedule_vm,
            "target": schedule_id,
            "status": LogStatus.success,
            "message": "Schedule deleted",
        }).execute()
    except Exception:
        pass


def toggle_schedule(schedule_id: str, user_id: str) -> ScheduleResponse:
    supabase = get_supabase_client()
    result = (
        supabase.table("vm_schedules")
        .select("*")
        .eq("id", schedule_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Schedule not found")

    row = result.data[0]
    new_enabled = not row["enabled"]

    now = datetime.now(timezone.utc).isoformat()
    updated = (
        supabase.table("vm_schedules")
        .update({"enabled": new_enabled, "updated_at": now})
        .eq("id", schedule_id)
        .execute()
    )

    if new_enabled:
        _add_job(row["id"], row["vm_id"], row["action"], row["cron_expr"], row["user_id"])
    else:
        _remove_job(schedule_id)

    return ScheduleResponse(**updated.data[0])
