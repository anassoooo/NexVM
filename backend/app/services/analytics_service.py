from datetime import datetime, timedelta, timezone

from fastapi import HTTPException

from app.config import settings
from app.db import get_supabase_client
from app.models.enums import VMStatus
from app.models.schemas import AdminAnalytics, AnalyticsTimeSeries, TimeSeriesPoint, UserAnalytics


def get_user_analytics(user_id: str) -> UserAnalytics:
    try:
        supabase = get_supabase_client()

        vm_result = (
            supabase.table("vms").select("status,disk_size").eq("user_id", user_id).execute()
        )
        vms = vm_result.data or []

        ai_result = (
            supabase.table("ai_usage").select("id").eq("user_id", user_id).execute()
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Analytics unavailable") from exc

    return UserAnalytics(
        total_vms=len(vms),
        running_vms=sum(1 for v in vms if v["status"] == VMStatus.running),
        stopped_vms=sum(1 for v in vms if v["status"] == VMStatus.stopped),
        error_vms=sum(1 for v in vms if v["status"] == VMStatus.error),
        total_ai_commands=len(ai_result.data or []),
        total_disk_used_mb=sum(v.get("disk_size", 0) for v in vms),
        disk_quota_mb=settings.VM_DISK_QUOTA_MB,
    )


def get_admin_analytics() -> AdminAnalytics:
    try:
        supabase = get_supabase_client()

        users_result = supabase.table("profiles").select("id").execute()
        vm_result = supabase.table("vms").select("status,disk_size").execute()
        ai_result = supabase.table("ai_usage").select("id").execute()
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Analytics unavailable") from exc

    vms = vm_result.data or []

    return AdminAnalytics(
        total_users=len(users_result.data or []),
        total_vms=len(vms),
        running_vms=sum(1 for v in vms if v["status"] == VMStatus.running),
        stopped_vms=sum(1 for v in vms if v["status"] == VMStatus.stopped),
        error_vms=sum(1 for v in vms if v["status"] == VMStatus.error),
        total_ai_commands=len(ai_result.data or []),
        total_disk_used_mb=sum(v.get("disk_size", 0) for v in vms),
        disk_quota_mb=settings.VM_DISK_QUOTA_MB,
    )


def get_user_timeseries(user_id: str, days: int = 30) -> AnalyticsTimeSeries:
    try:
        supabase = get_supabase_client()
        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

        vms_result = (
            supabase.table("vms")
            .select("created_at")
            .eq("user_id", user_id)
            .gte("created_at", since)
            .execute()
        )
        ai_result = (
            supabase.table("ai_usage")
            .select("created_at")
            .eq("user_id", user_id)
            .gte("created_at", since)
            .execute()
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Analytics unavailable") from exc

    return _build_timeseries(
        vms_created=vms_result.data or [],
        ai_commands=ai_result.data or [],
        days=days,
    )


def get_admin_timeseries(days: int = 30) -> AnalyticsTimeSeries:
    try:
        supabase = get_supabase_client()
        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

        vms_result = (
            supabase.table("vms")
            .select("created_at")
            .gte("created_at", since)
            .execute()
        )
        ai_result = (
            supabase.table("ai_usage")
            .select("created_at")
            .gte("created_at", since)
            .execute()
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Analytics unavailable") from exc

    return _build_timeseries(
        vms_created=vms_result.data or [],
        ai_commands=ai_result.data or [],
        days=days,
    )


def _build_timeseries(
    vms_created: list[dict],
    ai_commands: list[dict],
    days: int,
) -> AnalyticsTimeSeries:
    date_range = [
        (datetime.now(timezone.utc) - timedelta(days=i)).strftime("%Y-%m-%d")
        for i in range(days - 1, -1, -1)
    ]

    vm_counts: dict[str, int] = {d: 0 for d in date_range}
    ai_counts: dict[str, int] = {d: 0 for d in date_range}

    for row in vms_created:
        dt = row.get("created_at", "")[:10]
        if dt in vm_counts:
            vm_counts[dt] += 1

    for row in ai_commands:
        dt = row.get("created_at", "")[:10]
        if dt in ai_counts:
            ai_counts[dt] += 1

    vms_by_day: list[TimeSeriesPoint] = []
    cumulative = 0
    for d in date_range:
        cumulative += vm_counts[d]
        vms_by_day.append(TimeSeriesPoint(date=d, count=cumulative))

    return AnalyticsTimeSeries(
        vms_created=[TimeSeriesPoint(date=d, count=vm_counts[d]) for d in date_range],
        vms_by_day=vms_by_day,
        ai_commands_by_day=[TimeSeriesPoint(date=d, count=ai_counts[d]) for d in date_range],
    )
