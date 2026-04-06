import subprocess
from datetime import datetime, timezone

from fastapi import HTTPException

from app.db import get_supabase_client
from app.models.enums import LogAction, LogStatus
from app.models.schemas import VMCreate, VMResponse
from app.services.vbox_wrapper import build_vbox_path, run_vbox_command
from app.utils.logger import logger


def _log_action(
    user_id: str, action: LogAction, target: str, status: LogStatus, message: str
) -> None:
    try:
        supabase = get_supabase_client()
        supabase.table("logs").insert(
            {
                "user_id": user_id,
                "action": action,
                "target": target,
                "status": status,
                "message": message,
            }
        ).execute()
        logger.log(action, target, status, message, user_id)
    except Exception as exc:  # noqa: BLE001
        logger.log(
            action, target, LogStatus.failure, f"Log insert failed: {exc}", user_id
        )


def _vm_row_to_response(row: dict) -> VMResponse:
    return VMResponse(**row)


def _get_vm_or_404(vm_id: str, user_id: str) -> dict:
    supabase = get_supabase_client()
    result = (
        supabase.table("vms")
        .select("*")
        .eq("id", vm_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="VM not found")
    return result.data[0]


def list_vms(user_id: str) -> list[VMResponse]:
    supabase = get_supabase_client()
    result = (
        supabase.table("vms")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )
    return [_vm_row_to_response(row) for row in result.data]


def get_vm_status(vm_id: str, user_id: str) -> VMResponse:
    row = _get_vm_or_404(vm_id, user_id)
    return _vm_row_to_response(row)


def create_vm(data: VMCreate, user_id: str) -> VMResponse:
    vbox = build_vbox_path()
    cmd = [vbox, "createvm", "--name", data.name, "--register"]

    try:
        result = run_vbox_command(cmd)
    except FileNotFoundError:
        _log_action(
            user_id,
            LogAction.create_vm,
            "create_vm",
            LogStatus.failure,
            "VBoxManage not reachable",
        )
        raise HTTPException(
            status_code=503, detail="VBoxManage not reachable"
        ) from None
    except subprocess.TimeoutExpired:
        _log_action(
            user_id,
            LogAction.create_vm,
            "create_vm",
            LogStatus.failure,
            "Command timed out",
        )
        raise HTTPException(
            status_code=500, detail="VBoxManage command timed out"
        ) from None

    if result.returncode != 0:
        stderr = result.stderr.strip()
        if "already exists" in stderr:
            _log_action(
                user_id, LogAction.create_vm, "create_vm", LogStatus.failure, stderr
            )
            raise HTTPException(
                status_code=409, detail="A VM with this name already exists"
            )
        _log_action(
            user_id, LogAction.create_vm, "create_vm", LogStatus.failure, stderr
        )
        raise HTTPException(status_code=500, detail=f"VBoxManage failed: {stderr}")

    supabase = get_supabase_client()
    insert_result = (
        supabase.table("vms")
        .insert(
            {
                "user_id": user_id,
                "name": data.name,
                "os": data.os,
                "ram": data.ram,
                "status": "stopped",
            }
        )
        .execute()
    )

    vm = insert_result.data[0]
    _log_action(
        user_id,
        LogAction.create_vm,
        str(vm["id"]),
        LogStatus.success,
        f"VM '{data.name}' created",
    )
    return _vm_row_to_response(vm)


def start_vm(vm_id: str, user_id: str) -> VMResponse:
    vm = _get_vm_or_404(vm_id, user_id)
    status = vm["status"]

    if status in ("starting", "stopping"):
        raise HTTPException(
            status_code=409, detail="VM is already in a transitional state"
        )
    if status not in ("stopped", "error"):
        raise HTTPException(
            status_code=409, detail=f"Cannot start VM in '{status}' state"
        )

    supabase = get_supabase_client()
    now = datetime.now(timezone.utc).isoformat()
    supabase.table("vms").update(
        {"status": "starting", "error_message": None, "updated_at": now}
    ).eq("id", vm_id).execute()

    vbox = build_vbox_path()
    cmd = [vbox, "startvm", vm["name"], "--type", "headless"]

    try:
        result = run_vbox_command(cmd)
    except FileNotFoundError:
        _update_vm_error(vm_id, "VBoxManage not reachable", user_id, LogAction.start_vm)
        raise HTTPException(
            status_code=503, detail="VBoxManage not reachable"
        ) from None
    except subprocess.TimeoutExpired:
        _update_vm_error(vm_id, "Command timed out", user_id, LogAction.start_vm)
        raise HTTPException(
            status_code=500, detail="VBoxManage command timed out"
        ) from None

    if result.returncode != 0:
        stderr = result.stderr.strip()
        _update_vm_error(vm_id, stderr, user_id, LogAction.start_vm)
        raise HTTPException(status_code=500, detail=f"VBoxManage failed: {stderr}")

    now = datetime.now(timezone.utc).isoformat()
    updated = (
        supabase.table("vms")
        .update({"status": "running", "error_message": None, "updated_at": now})
        .eq("id", vm_id)
        .execute()
    )
    _log_action(
        user_id,
        LogAction.start_vm,
        vm_id,
        LogStatus.success,
        f"VM '{vm['name']}' started",
    )

    return _vm_row_to_response(updated.data[0])


def stop_vm(vm_id: str, user_id: str) -> VMResponse:
    vm = _get_vm_or_404(vm_id, user_id)
    status = vm["status"]

    if status in ("starting", "stopping"):
        raise HTTPException(
            status_code=409, detail="VM is already in a transitional state"
        )
    if status != "running":
        raise HTTPException(
            status_code=409, detail=f"Cannot stop VM in '{status}' state"
        )

    supabase = get_supabase_client()
    now = datetime.now(timezone.utc).isoformat()
    supabase.table("vms").update({"status": "stopping", "updated_at": now}).eq(
        "id", vm_id
    ).execute()

    vbox = build_vbox_path()
    cmd = [vbox, "controlvm", vm["name"], "poweroff"]

    try:
        result = run_vbox_command(cmd)
    except FileNotFoundError:
        _update_vm_error(vm_id, "VBoxManage not reachable", user_id, LogAction.stop_vm)
        raise HTTPException(
            status_code=503, detail="VBoxManage not reachable"
        ) from None
    except subprocess.TimeoutExpired:
        _update_vm_error(vm_id, "Command timed out", user_id, LogAction.stop_vm)
        raise HTTPException(
            status_code=500, detail="VBoxManage command timed out"
        ) from None

    if result.returncode != 0:
        stderr = result.stderr.strip()
        _update_vm_error(vm_id, stderr, user_id, LogAction.stop_vm)
        raise HTTPException(status_code=500, detail=f"VBoxManage failed: {stderr}")

    now = datetime.now(timezone.utc).isoformat()
    updated = (
        supabase.table("vms")
        .update({"status": "stopped", "error_message": None, "updated_at": now})
        .eq("id", vm_id)
        .execute()
    )
    _log_action(
        user_id,
        LogAction.stop_vm,
        vm_id,
        LogStatus.success,
        f"VM '{vm['name']}' stopped",
    )

    return _vm_row_to_response(updated.data[0])


def delete_vm(vm_id: str, user_id: str) -> None:
    vm = _get_vm_or_404(vm_id, user_id)
    status = vm["status"]

    if status != "stopped":
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete VM in '{status}' state — stop it first",
        )

    vbox = build_vbox_path()
    cmd = [vbox, "unregistervm", vm["name"], "--delete"]

    try:
        result = run_vbox_command(cmd)
    except FileNotFoundError:
        _log_action(
            user_id,
            LogAction.delete_vm,
            vm_id,
            LogStatus.failure,
            "VBoxManage not reachable",
        )
        raise HTTPException(
            status_code=503, detail="VBoxManage not reachable"
        ) from None
    except subprocess.TimeoutExpired:
        _log_action(
            user_id, LogAction.delete_vm, vm_id, LogStatus.failure, "Command timed out"
        )
        raise HTTPException(
            status_code=500, detail="VBoxManage command timed out"
        ) from None

    if result.returncode != 0:
        stderr = result.stderr.strip()
        _log_action(user_id, LogAction.delete_vm, vm_id, LogStatus.failure, stderr)
        raise HTTPException(status_code=500, detail=f"VBoxManage failed: {stderr}")

    supabase = get_supabase_client()
    supabase.table("vms").delete().eq("id", vm_id).execute()
    _log_action(
        user_id,
        LogAction.delete_vm,
        vm_id,
        LogStatus.success,
        f"VM '{vm['name']}' deleted",
    )


def _update_vm_error(
    vm_id: str, error_message: str, user_id: str, action: LogAction
) -> None:
    supabase = get_supabase_client()
    now = datetime.now(timezone.utc).isoformat()
    supabase.table("vms").update(
        {"status": "error", "error_message": error_message, "updated_at": now}
    ).eq("id", vm_id).execute()
    _log_action(user_id, action, vm_id, LogStatus.failure, error_message)
