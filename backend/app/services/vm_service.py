import os
import re
import subprocess
from datetime import datetime, timezone
from typing import Callable

from fastapi import HTTPException

from app.config import settings
from app.db import get_supabase_client
from app.models.enums import LogAction, LogStatus
import json

from app.models.schemas import SnapshotResponse, VMCreate, VMResponse
from app.services.vbox_wrapper import (
    VBOX_STATE_MAP,
    build_vbox_path,
    extract_vbox_uuid,
    get_ostype,
    get_vm_disk_path,
    get_storage_base,
    parse_vbox_state,
    run_vbox_command,
)
from app.utils.logger import logger


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

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
        logger.log(action, target, LogStatus.failure, f"Log insert failed: {exc}", user_id)


def _vm_row_to_response(row: dict) -> VMResponse:
    return VMResponse(**row)


def _get_vm_or_404(vm_id: str, user_id: str | None) -> dict:
    supabase = get_supabase_client()
    query = supabase.table("vms").select("*").eq("id", vm_id)
    if user_id is not None:
        query = query.eq("user_id", user_id)
    result = query.execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="VM not found")
    return result.data[0]


def _check_disk_quota(user_id: str, new_disk_mb: int) -> None:
    supabase = get_supabase_client()
    result = supabase.table("vms").select("disk_size").eq("user_id", user_id).execute()
    used_mb = sum(row.get("disk_size", 0) for row in (result.data or []))
    if used_mb + new_disk_mb > settings.VM_DISK_QUOTA_MB:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Disk quota exceeded — {used_mb + new_disk_mb} MB needed, "
                f"limit is {settings.VM_DISK_QUOTA_MB} MB"
            ),
        )


def _update_vm_error(vm_id: str, error_message: str, user_id: str, action: LogAction) -> None:
    supabase = get_supabase_client()
    now = datetime.now(timezone.utc).isoformat()
    supabase.table("vms").update(
        {"status": "error", "error_message": error_message, "updated_at": now}
    ).eq("id", vm_id).execute()
    _log_action(user_id, action, vm_id, LogStatus.failure, error_message)


def _run_vbox(
    cmd: list[str],
    user_id: str,
    action: LogAction,
    step: str,
    on_failure: Callable | None = None,
) -> subprocess.CompletedProcess:
    """Run a VBoxManage command with uniform error handling."""
    try:
        result = run_vbox_command(cmd)
    except FileNotFoundError:
        if on_failure:
            on_failure()
        _log_action(user_id, action, step, LogStatus.failure, "VBoxManage not reachable")
        raise HTTPException(status_code=503, detail="VBoxManage not reachable") from None
    except subprocess.TimeoutExpired:
        if on_failure:
            on_failure()
        _log_action(user_id, action, step, LogStatus.failure, "Command timed out")
        raise HTTPException(status_code=500, detail="VBoxManage command timed out") from None

    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip()
        if on_failure:
            on_failure()
        _log_action(user_id, action, step, LogStatus.failure, stderr)
        if "already exists" in stderr.lower():
            raise HTTPException(status_code=409, detail="A VM with this name already exists")
        raise HTTPException(status_code=500, detail=f"VBoxManage error ({step}): {stderr}")

    return result


# ---------------------------------------------------------------------------
# Public service functions
# ---------------------------------------------------------------------------

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


def list_all_vms() -> list[VMResponse]:
    supabase = get_supabase_client()
    result = (
        supabase.table("vms")
        .select("*")
        .order("created_at", desc=True)
        .execute()
    )
    return [_vm_row_to_response(row) for row in result.data]


def get_vm_status(vm_id: str, user_id: str) -> VMResponse:
    row = _get_vm_or_404(vm_id, user_id)
    return _vm_row_to_response(row)


def sync_vm_status(vm_id: str, user_id: str) -> VMResponse:
    """Query VBoxManage for the real VM state and update DB if it differs."""
    vm = _get_vm_or_404(vm_id, user_id)
    vbox = build_vbox_path()

    try:
        result = run_vbox_command([vbox, "showvminfo", vm["name"], "--machinereadable"])
    except (FileNotFoundError, subprocess.TimeoutExpired, ValueError):
        return _vm_row_to_response(vm)

    if result.returncode != 0:
        return _vm_row_to_response(vm)

    vbox_state = parse_vbox_state(result.stdout)
    new_status = VBOX_STATE_MAP.get(vbox_state or "", vm["status"])

    if new_status != vm["status"]:
        supabase = get_supabase_client()
        now = datetime.now(timezone.utc).isoformat()
        updated = (
            supabase.table("vms")
            .update({"status": new_status, "updated_at": now})
            .eq("id", vm_id)
            .execute()
        )
        return _vm_row_to_response(updated.data[0])

    return _vm_row_to_response(vm)


def create_vm(data: VMCreate, user_id: str) -> VMResponse:
    supabase = get_supabase_client()

    # Quota check
    count_result = (
        supabase.table("vms").select("id", count="exact").eq("user_id", user_id).execute()
    )
    if (count_result.count or 0) >= settings.VM_QUOTA_PER_USER:
        raise HTTPException(
            status_code=409,
            detail=f"VM quota reached — maximum {settings.VM_QUOTA_PER_USER} VMs per user",
        )
    _check_disk_quota(user_id, data.disk_size)

    vbox = build_vbox_path()
    os_type = get_ostype(data.os)
    disk_path = get_vm_disk_path(data.name)
    storage_base = get_storage_base()
    vm_name = data.name

    try:
        os.makedirs(storage_base, exist_ok=True)
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"VM storage path unavailable: {exc}") from exc

    def cleanup() -> None:
        """Best-effort VBox cleanup if creation fails mid-way."""
        try:
            run_vbox_command([vbox, "unregistervm", vm_name, "--delete"])
        except Exception:  # noqa: BLE001
            pass

    # Step 1 — Register VM
    create_cmd = [vbox, "createvm", "--name", vm_name, "--ostype", os_type, "--register",
                  "--basefolder", storage_base]
    result = _run_vbox(create_cmd, user_id, LogAction.create_vm, "createvm")
    vbox_id = extract_vbox_uuid(result.stdout)

    # Step 2 — Configure hardware (RAM, CPU, VRAM, boot order)
    _run_vbox(
        [vbox, "modifyvm", vm_name,
         "--memory", str(data.ram),
         "--cpus", str(data.cpu),
         "--vram", "16",
         "--acpi", "on",
         "--ioapic", "on",
         "--boot1", "disk",
         "--boot2", "none",
         "--boot3", "none"],
        user_id, LogAction.create_vm, "modifyvm hardware", cleanup,
    )

    # Step 3 — Add SATA controller
    _run_vbox(
        [vbox, "storagectl", vm_name, "--name", "SATA", "--add", "sata",
         "--controller", "IntelAhci", "--portcount", "2"],
        user_id, LogAction.create_vm, "storagectl", cleanup,
    )

    # Step 4 — Create virtual disk (VDI)
    _run_vbox(
        [vbox, "createmedium", "disk",
         "--filename", disk_path,
         "--size", str(data.disk_size),
         "--format", "VDI"],
        user_id, LogAction.create_vm, "createmedium", cleanup,
    )

    # Step 5 — Attach disk to SATA port 0
    _run_vbox(
        [vbox, "storageattach", vm_name,
         "--storagectl", "SATA",
         "--port", "0", "--device", "0",
         "--type", "hdd", "--medium", disk_path],
        user_id, LogAction.create_vm, "storageattach", cleanup,
    )

    # Step 6 — NAT network adapter
    _run_vbox(
        [vbox, "modifyvm", vm_name,
         "--nic1", "nat", "--nictype1", "82540EM",
         "--natpf1", "ssh,tcp,,2222,,22"],
        user_id, LogAction.create_vm, "modifyvm network", cleanup,
    )

    # Persist to DB
    insert_result = (
        supabase.table("vms")
        .insert({
            "user_id": user_id,
            "name": vm_name,
            "os": data.os,
            "ram": data.ram,
            "cpu": data.cpu,
            "disk_size": data.disk_size,
            "status": "stopped",
            "vbox_id": vbox_id,
        })
        .execute()
    )

    vm = insert_result.data[0]
    _log_action(
        user_id, LogAction.create_vm, str(vm["id"]),
        LogStatus.success, f"VM '{vm_name}' created ({data.cpu} vCPU, {data.ram} MB RAM, {data.disk_size} MB disk)",
    )
    return _vm_row_to_response(vm)


def start_vm(vm_id: str, user_id: str | None, actor_id: str | None = None) -> VMResponse:
    log_user = actor_id if actor_id is not None else user_id
    vm = _get_vm_or_404(vm_id, user_id)
    status = vm["status"]

    if status in ("starting", "stopping"):
        raise HTTPException(status_code=409, detail="VM is already in a transitional state")
    if status not in ("stopped", "error"):
        raise HTTPException(status_code=409, detail=f"Cannot start VM in '{status}' state")

    supabase = get_supabase_client()
    now = datetime.now(timezone.utc).isoformat()
    supabase.table("vms").update(
        {"status": "starting", "error_message": None, "updated_at": now}
    ).eq("id", vm_id).execute()

    vbox = build_vbox_path()
    try:
        result = run_vbox_command([vbox, "startvm", vm["name"], "--type", "headless"])
    except FileNotFoundError:
        _update_vm_error(vm_id, "VBoxManage not reachable", log_user, LogAction.start_vm)
        raise HTTPException(status_code=503, detail="VBoxManage not reachable") from None
    except subprocess.TimeoutExpired:
        _update_vm_error(vm_id, "Command timed out", log_user, LogAction.start_vm)
        raise HTTPException(status_code=500, detail="VBoxManage command timed out") from None

    if result.returncode != 0:
        stderr = result.stderr.strip()
        _update_vm_error(vm_id, stderr, log_user, LogAction.start_vm)
        raise HTTPException(status_code=500, detail=f"VBoxManage failed: {stderr}")

    now = datetime.now(timezone.utc).isoformat()
    updated = (
        supabase.table("vms")
        .update({"status": "running", "error_message": None, "updated_at": now})
        .eq("id", vm_id)
        .execute()
    )
    _log_action(log_user, LogAction.start_vm, vm_id, LogStatus.success, f"VM '{vm['name']}' started")
    return _vm_row_to_response(updated.data[0])


def stop_vm(vm_id: str, user_id: str | None, actor_id: str | None = None) -> VMResponse:
    log_user = actor_id if actor_id is not None else user_id
    vm = _get_vm_or_404(vm_id, user_id)
    status = vm["status"]

    if status in ("starting", "stopping"):
        raise HTTPException(status_code=409, detail="VM is already in a transitional state")
    if status != "running":
        raise HTTPException(status_code=409, detail=f"Cannot stop VM in '{status}' state")

    supabase = get_supabase_client()
    now = datetime.now(timezone.utc).isoformat()
    supabase.table("vms").update({"status": "stopping", "updated_at": now}).eq("id", vm_id).execute()

    vbox = build_vbox_path()
    try:
        # poweroff is synchronous — VM is guaranteed stopped when it returns 0.
        # acpipowerbutton is async and returns 0 even when the guest ignores it (no OS).
        result = run_vbox_command([vbox, "controlvm", vm["name"], "poweroff"])
    except FileNotFoundError:
        _update_vm_error(vm_id, "VBoxManage not reachable", log_user, LogAction.stop_vm)
        raise HTTPException(status_code=503, detail="VBoxManage not reachable") from None
    except subprocess.TimeoutExpired:
        _update_vm_error(vm_id, "Command timed out", log_user, LogAction.stop_vm)
        raise HTTPException(status_code=500, detail="VBoxManage command timed out") from None

    if result.returncode != 0:
        stderr = result.stderr.strip()
        _update_vm_error(vm_id, stderr, log_user, LogAction.stop_vm)
        raise HTTPException(status_code=500, detail=f"VBoxManage failed: {stderr}")

    # Verify VirtualBox actually reports poweroff before trusting the DB update.
    try:
        info = run_vbox_command([vbox, "showvminfo", vm["name"], "--machinereadable"])
        vbox_state = parse_vbox_state(info.stdout) if info.returncode == 0 else None
    except Exception:  # noqa: BLE001
        vbox_state = None

    actual_status = VBOX_STATE_MAP.get(vbox_state or "", "stopped")

    now = datetime.now(timezone.utc).isoformat()
    updated = (
        supabase.table("vms")
        .update({"status": actual_status, "error_message": None, "updated_at": now})
        .eq("id", vm_id)
        .execute()
    )
    _log_action(log_user, LogAction.stop_vm, vm_id, LogStatus.success, f"VM '{vm['name']}' stopped (vbox state: {actual_status})")
    return _vm_row_to_response(updated.data[0])


def delete_vm(vm_id: str, user_id: str | None, actor_id: str | None = None) -> None:
    log_user = actor_id if actor_id is not None else user_id
    vm = _get_vm_or_404(vm_id, user_id)
    status = vm["status"]

    if status not in ("stopped", "error"):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete VM in '{status}' state — stop it first",
        )

    vbox = build_vbox_path()
    try:
        result = run_vbox_command([vbox, "unregistervm", vm["name"], "--delete"])
    except FileNotFoundError:
        _log_action(log_user, LogAction.delete_vm, vm_id, LogStatus.failure, "VBoxManage not reachable")
        raise HTTPException(status_code=503, detail="VBoxManage not reachable") from None
    except subprocess.TimeoutExpired:
        _log_action(log_user, LogAction.delete_vm, vm_id, LogStatus.failure, "Command timed out")
        raise HTTPException(status_code=500, detail="VBoxManage command timed out") from None

    # Accept return code 1 when VM doesn't exist in VBox (DB and VBox out of sync) — still delete from DB
    if result.returncode != 0:
        stderr = result.stderr.strip()
        if "could not find" not in stderr.lower() and "does not exist" not in stderr.lower():
            _log_action(log_user, LogAction.delete_vm, vm_id, LogStatus.failure, stderr)
            raise HTTPException(status_code=500, detail=f"VBoxManage failed: {stderr}")

    supabase = get_supabase_client()
    supabase.table("vms").delete().eq("id", vm_id).execute()
    _log_action(log_user, LogAction.delete_vm, vm_id, LogStatus.success, f"VM '{vm['name']}' deleted")


def attach_iso(vm_id: str, iso_path: str, user_id: str) -> VMResponse:
    vm = _get_vm_or_404(vm_id, user_id)
    if vm["status"] != "stopped":
        raise HTTPException(status_code=409, detail=f"Cannot attach ISO — VM is '{vm['status']}' (must be stopped)")
    if not os.path.exists(iso_path):
        raise HTTPException(status_code=422, detail=f"ISO file not found: {iso_path}")

    vbox = build_vbox_path()
    vm_name = vm["name"]

    # Add IDE controller — swallow "already exists" (idempotent)
    try:
        ctl_result = run_vbox_command([vbox, "storagectl", vm_name, "--name", "IDE", "--add", "ide", "--controller", "PIIX4"])
        if ctl_result.returncode != 0:
            stderr = ctl_result.stderr.strip().lower()
            if "already exists" not in stderr:
                raise HTTPException(status_code=500, detail=f"VBoxManage error (storagectl): {ctl_result.stderr.strip()}")
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="VBoxManage not reachable") from None
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail="VBoxManage command timed out") from None

    _run_vbox(
        [vbox, "storageattach", vm_name, "--storagectl", "IDE",
         "--port", "0", "--device", "0", "--type", "dvddrive", "--medium", iso_path],
        user_id, LogAction.attach_iso, "storageattach iso",
    )

    # Boot from DVD first so the ISO is used before the (empty) hard disk
    _run_vbox(
        [vbox, "modifyvm", vm_name, "--boot1", "dvd", "--boot2", "disk", "--boot3", "none"],
        user_id, LogAction.attach_iso, "modifyvm boot order",
    )

    supabase = get_supabase_client()
    now = datetime.now(timezone.utc).isoformat()
    updated = supabase.table("vms").update({"iso_path": iso_path, "updated_at": now}).eq("id", vm_id).execute()
    _log_action(user_id, LogAction.attach_iso, vm_name, LogStatus.success, iso_path)
    return _vm_row_to_response(updated.data[0])


def detach_iso(vm_id: str, user_id: str) -> VMResponse:
    vm = _get_vm_or_404(vm_id, user_id)
    if vm["status"] != "stopped":
        raise HTTPException(status_code=409, detail=f"Cannot detach ISO — VM is '{vm['status']}' (must be stopped)")
    if not vm.get("iso_path"):
        raise HTTPException(status_code=409, detail="No ISO attached to this VM")

    vbox = build_vbox_path()
    vm_name = vm["name"]

    _run_vbox(
        [vbox, "storageattach", vm_name, "--storagectl", "IDE",
         "--port", "0", "--device", "0", "--type", "dvddrive", "--medium", "emptydrive"],
        user_id, LogAction.detach_iso, "storageattach emptydrive",
    )

    # Restore disk-first boot order now that the ISO is gone
    _run_vbox(
        [vbox, "modifyvm", vm_name, "--boot1", "disk", "--boot2", "none", "--boot3", "none"],
        user_id, LogAction.detach_iso, "modifyvm boot order",
    )

    supabase = get_supabase_client()
    now = datetime.now(timezone.utc).isoformat()
    updated = supabase.table("vms").update({"iso_path": None, "updated_at": now}).eq("id", vm_id).execute()
    _log_action(user_id, LogAction.detach_iso, vm_name, LogStatus.success, "detached")
    return _vm_row_to_response(updated.data[0])


def enable_vrde(vm_id: str, port: int, user_id: str) -> VMResponse:
    vm = _get_vm_or_404(vm_id, user_id)
    if vm["status"] != "stopped":
        raise HTTPException(status_code=409, detail=f"Cannot enable VRDE — VM is '{vm['status']}' (must be stopped)")

    supabase = get_supabase_client()
    conflict = supabase.table("vms").select("id").eq("vrde_port", port).neq("id", vm_id).execute()
    if conflict.data:
        raise HTTPException(status_code=409, detail=f"Port {port} is already in use by another VM")

    vbox = build_vbox_path()
    vm_name = vm["name"]

    _run_vbox(
        [vbox, "modifyvm", vm_name, "--vrde", "on", "--vrdeport", str(port)],
        user_id, LogAction.enable_vrde, "modifyvm vrde",
    )

    now = datetime.now(timezone.utc).isoformat()
    updated = supabase.table("vms").update(
        {"vrde_enabled": True, "vrde_port": port, "updated_at": now}
    ).eq("id", vm_id).execute()
    _log_action(user_id, LogAction.enable_vrde, vm_name, LogStatus.success, str(port))
    return _vm_row_to_response(updated.data[0])


def disable_vrde(vm_id: str, user_id: str) -> VMResponse:
    vm = _get_vm_or_404(vm_id, user_id)
    if vm["status"] != "stopped":
        raise HTTPException(status_code=409, detail=f"Cannot disable VRDE — VM is '{vm['status']}' (must be stopped)")
    if not vm.get("vrde_enabled"):
        raise HTTPException(status_code=409, detail="VRDE is already disabled on this VM")

    vbox = build_vbox_path()
    vm_name = vm["name"]

    _run_vbox(
        [vbox, "modifyvm", vm_name, "--vrde", "off"],
        user_id, LogAction.disable_vrde, "modifyvm vrde off",
    )

    supabase = get_supabase_client()
    now = datetime.now(timezone.utc).isoformat()
    updated = supabase.table("vms").update(
        {"vrde_enabled": False, "vrde_port": None, "updated_at": now}
    ).eq("id", vm_id).execute()
    _log_action(user_id, LogAction.disable_vrde, vm_name, LogStatus.success, "disabled")
    return _vm_row_to_response(updated.data[0])


def force_reset_vm(vm_id: str, actor_id: str) -> VMResponse:
    """Admin: hard-poweroff then reset DB status to stopped."""
    vm = _get_vm_or_404(vm_id, user_id=None)
    vbox = build_vbox_path()

    # Best-effort hard poweroff
    try:
        run_vbox_command([vbox, "controlvm", vm["name"], "poweroff"])
    except Exception:  # noqa: BLE001
        pass

    supabase = get_supabase_client()
    now = datetime.now(timezone.utc).isoformat()
    updated = (
        supabase.table("vms")
        .update({"status": "stopped", "error_message": None, "updated_at": now})
        .eq("id", vm_id)
        .execute()
    )
    _log_action(actor_id, LogAction.force_reset_vm, vm_id, LogStatus.success, "Force-poweroff and reset to stopped")
    return _vm_row_to_response(updated.data[0])


# ---------------------------------------------------------------------------
# P2 — Lifecycle features
# ---------------------------------------------------------------------------

def modify_vm(vm_id: str, ram: int | None, cpu: int | None, user_id: str) -> VMResponse:
    vm = _get_vm_or_404(vm_id, user_id)
    if vm["status"] != "stopped":
        raise HTTPException(status_code=409, detail=f"Cannot modify VM in '{vm['status']}' state (must be stopped)")

    vbox = build_vbox_path()
    vm_name = vm["name"]
    args: list[str] = []
    if ram is not None:
        args += ["--memory", str(ram)]
    if cpu is not None:
        args += ["--cpus", str(cpu)]

    _run_vbox([vbox, "modifyvm", vm_name, *args], user_id, LogAction.modify_vm, "modifyvm modify")

    updates: dict = {"updated_at": datetime.now(timezone.utc).isoformat()}
    if ram is not None:
        updates["ram"] = ram
    if cpu is not None:
        updates["cpu"] = cpu

    supabase = get_supabase_client()
    updated = supabase.table("vms").update(updates).eq("id", vm_id).execute()
    _log_action(user_id, LogAction.modify_vm, vm_name, LogStatus.success, f"ram={ram} cpu={cpu}")
    return _vm_row_to_response(updated.data[0])


def pause_vm(vm_id: str, user_id: str) -> VMResponse:
    vm = _get_vm_or_404(vm_id, user_id)
    if vm["status"] != "running":
        raise HTTPException(status_code=409, detail=f"Cannot pause VM in '{vm['status']}' state (must be running)")

    vbox = build_vbox_path()
    try:
        result = run_vbox_command([vbox, "controlvm", vm["name"], "pause"])
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="VBoxManage not reachable") from None
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail="VBoxManage command timed out") from None

    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=f"VBoxManage failed: {result.stderr.strip()}")

    supabase = get_supabase_client()
    now = datetime.now(timezone.utc).isoformat()
    updated = supabase.table("vms").update({"status": "paused", "updated_at": now}).eq("id", vm_id).execute()
    _log_action(user_id, LogAction.pause_vm, vm_id, LogStatus.success, f"VM '{vm['name']}' paused")
    return _vm_row_to_response(updated.data[0])


def resume_vm(vm_id: str, user_id: str) -> VMResponse:
    vm = _get_vm_or_404(vm_id, user_id)
    if vm["status"] != "paused":
        raise HTTPException(status_code=409, detail=f"Cannot resume VM in '{vm['status']}' state (must be paused)")

    vbox = build_vbox_path()
    try:
        result = run_vbox_command([vbox, "controlvm", vm["name"], "resume"])
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="VBoxManage not reachable") from None
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail="VBoxManage command timed out") from None

    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=f"VBoxManage failed: {result.stderr.strip()}")

    supabase = get_supabase_client()
    now = datetime.now(timezone.utc).isoformat()
    updated = supabase.table("vms").update({"status": "running", "updated_at": now}).eq("id", vm_id).execute()
    _log_action(user_id, LogAction.resume_vm, vm_id, LogStatus.success, f"VM '{vm['name']}' resumed")
    return _vm_row_to_response(updated.data[0])


def save_state(vm_id: str, user_id: str) -> VMResponse:
    vm = _get_vm_or_404(vm_id, user_id)
    if vm["status"] != "running":
        raise HTTPException(status_code=409, detail=f"Cannot save state of VM in '{vm['status']}' state (must be running)")

    supabase = get_supabase_client()
    now = datetime.now(timezone.utc).isoformat()
    supabase.table("vms").update({"status": "stopping", "updated_at": now}).eq("id", vm_id).execute()

    vbox = build_vbox_path()
    try:
        result = run_vbox_command([vbox, "controlvm", vm["name"], "savestate"])
    except FileNotFoundError:
        _update_vm_error(vm_id, "VBoxManage not reachable", user_id, LogAction.save_state)
        raise HTTPException(status_code=503, detail="VBoxManage not reachable") from None
    except subprocess.TimeoutExpired:
        _update_vm_error(vm_id, "Command timed out", user_id, LogAction.save_state)
        raise HTTPException(status_code=500, detail="VBoxManage command timed out") from None

    if result.returncode != 0:
        stderr = result.stderr.strip()
        _update_vm_error(vm_id, stderr, user_id, LogAction.save_state)
        raise HTTPException(status_code=500, detail=f"VBoxManage failed: {stderr}")

    now = datetime.now(timezone.utc).isoformat()
    updated = supabase.table("vms").update({"status": "stopped", "updated_at": now}).eq("id", vm_id).execute()
    _log_action(user_id, LogAction.save_state, vm_id, LogStatus.success, f"VM '{vm['name']}' state saved")
    return _vm_row_to_response(updated.data[0])


def add_port_rule(
    vm_id: str, name: str, protocol: str, host_port: int, guest_port: int, user_id: str
) -> VMResponse:
    vm = _get_vm_or_404(vm_id, user_id)
    if vm["status"] != "stopped":
        raise HTTPException(status_code=409, detail=f"Cannot modify port rules — VM is '{vm['status']}' (must be stopped)")

    existing: list[dict] = vm.get("nat_rules") or []
    if any(r["name"] == name for r in existing):
        raise HTTPException(status_code=409, detail=f"Port rule '{name}' already exists on this VM")

    _run_vbox(
        [build_vbox_path(), "modifyvm", vm["name"], "--natpf1", f"{name},{protocol},,{host_port},,{guest_port}"],
        user_id, LogAction.add_port_rule, "modifyvm natpf1",
    )

    new_rules = existing + [{"name": name, "protocol": protocol, "host_port": host_port, "guest_port": guest_port}]
    supabase = get_supabase_client()
    now = datetime.now(timezone.utc).isoformat()
    updated = supabase.table("vms").update({"nat_rules": json.dumps(new_rules), "updated_at": now}).eq("id", vm_id).execute()
    _log_action(user_id, LogAction.add_port_rule, vm["name"], LogStatus.success, f"{name}:{host_port}->{guest_port}")
    return _vm_row_to_response(updated.data[0])


def remove_port_rule(vm_id: str, name: str, user_id: str) -> VMResponse:
    vm = _get_vm_or_404(vm_id, user_id)
    if vm["status"] != "stopped":
        raise HTTPException(status_code=409, detail=f"Cannot modify port rules — VM is '{vm['status']}' (must be stopped)")

    existing: list[dict] = vm.get("nat_rules") or []
    if not any(r["name"] == name for r in existing):
        raise HTTPException(status_code=404, detail=f"Port rule '{name}' not found on this VM")

    _run_vbox(
        [build_vbox_path(), "modifyvm", vm["name"], "--natpf1", f"delete {name}"],
        user_id, LogAction.remove_port_rule, "modifyvm natpf1 delete",
    )

    new_rules = [r for r in existing if r["name"] != name]
    supabase = get_supabase_client()
    now = datetime.now(timezone.utc).isoformat()
    updated = supabase.table("vms").update({"nat_rules": json.dumps(new_rules), "updated_at": now}).eq("id", vm_id).execute()
    _log_action(user_id, LogAction.remove_port_rule, vm["name"], LogStatus.success, name)
    return _vm_row_to_response(updated.data[0])


def take_snapshot(vm_id: str, name: str, description: str, user_id: str) -> SnapshotResponse:
    vm = _get_vm_or_404(vm_id, user_id)
    if vm["status"] != "stopped":
        raise HTTPException(status_code=409, detail=f"Cannot take snapshot — VM is '{vm['status']}' (must be stopped)")

    supabase = get_supabase_client()
    existing = supabase.table("vm_snapshots").select("id").eq("vm_id", vm_id).eq("name", name).execute()
    if existing.data:
        raise HTTPException(status_code=409, detail=f"Snapshot '{name}' already exists on this VM")

    _run_vbox(
        [build_vbox_path(), "snapshot", vm["name"], "take", name, "--description", description],
        user_id, LogAction.take_snapshot, "snapshot take",
    )

    inserted = supabase.table("vm_snapshots").insert(
        {"vm_id": vm_id, "name": name, "description": description or None}
    ).execute()
    _log_action(user_id, LogAction.take_snapshot, vm["name"], LogStatus.success, name)
    return SnapshotResponse(**inserted.data[0])


def restore_snapshot(vm_id: str, name: str, user_id: str) -> VMResponse:
    vm = _get_vm_or_404(vm_id, user_id)
    if vm["status"] != "stopped":
        raise HTTPException(status_code=409, detail=f"Cannot restore snapshot — VM is '{vm['status']}' (must be stopped)")

    supabase = get_supabase_client()
    existing = supabase.table("vm_snapshots").select("id").eq("vm_id", vm_id).eq("name", name).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail=f"Snapshot '{name}' not found on this VM")

    _run_vbox(
        [build_vbox_path(), "snapshot", vm["name"], "restore", name],
        user_id, LogAction.restore_snapshot, "snapshot restore",
    )

    _log_action(user_id, LogAction.restore_snapshot, vm["name"], LogStatus.success, name)
    return _vm_row_to_response(vm)


def delete_snapshot(vm_id: str, name: str, user_id: str) -> None:
    vm = _get_vm_or_404(vm_id, user_id)
    if vm["status"] != "stopped":
        raise HTTPException(status_code=409, detail=f"Cannot delete snapshot — VM is '{vm['status']}' (must be stopped)")

    supabase = get_supabase_client()
    existing = supabase.table("vm_snapshots").select("id").eq("vm_id", vm_id).eq("name", name).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail=f"Snapshot '{name}' not found on this VM")

    _run_vbox(
        [build_vbox_path(), "snapshot", vm["name"], "delete", name],
        user_id, LogAction.delete_snapshot, "snapshot delete",
    )

    supabase.table("vm_snapshots").delete().eq("vm_id", vm_id).eq("name", name).execute()
    _log_action(user_id, LogAction.delete_snapshot, vm["name"], LogStatus.success, name)


def list_snapshots(vm_id: str, user_id: str) -> list[SnapshotResponse]:
    _get_vm_or_404(vm_id, user_id)
    supabase = get_supabase_client()
    result = (
        supabase.table("vm_snapshots")
        .select("*")
        .eq("vm_id", vm_id)
        .order("created_at", desc=True)
        .execute()
    )
    return [SnapshotResponse(**row) for row in result.data]


# ---------------------------------------------------------------------------
# P3 — Clone, Export / Import OVA
# ---------------------------------------------------------------------------

def clone_vm(vm_id: str, new_name: str, user_id: str) -> VMResponse:
    vm = _get_vm_or_404(vm_id, user_id)
    if vm["status"] not in ("stopped", "error"):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot clone VM in '{vm['status']}' state (must be stopped or error)",
        )

    supabase = get_supabase_client()

    count_result = (
        supabase.table("vms").select("id", count="exact").eq("user_id", user_id).execute()
    )
    if (count_result.count or 0) >= settings.VM_QUOTA_PER_USER:
        raise HTTPException(
            status_code=409,
            detail=f"VM quota reached — maximum {settings.VM_QUOTA_PER_USER} VMs per user",
        )
    _check_disk_quota(user_id, vm["disk_size"])

    name_check = (
        supabase.table("vms").select("id").eq("user_id", user_id).eq("name", new_name).execute()
    )
    if name_check.data:
        raise HTTPException(status_code=409, detail=f"A VM named '{new_name}' already exists")

    vbox = build_vbox_path()
    _run_vbox(
        [vbox, "clonevm", vm["name"], "--name", new_name, "--register"],
        user_id, LogAction.clone_vm, "clonevm",
    )

    vbox_id: str | None = None
    info = run_vbox_command([vbox, "showvminfo", new_name, "--machinereadable"])
    if info.returncode == 0:
        for line in info.stdout.splitlines():
            if line.startswith("UUID="):
                vbox_id = line.split("=", 1)[1].strip('"')
                break

    now = datetime.now(timezone.utc).isoformat()
    inserted = supabase.table("vms").insert({
        "user_id": user_id,
        "name": new_name,
        "os": vm["os"],
        "ram": vm["ram"],
        "cpu": vm["cpu"],
        "disk_size": vm["disk_size"],
        "status": "stopped",
        "vbox_id": vbox_id,
        "created_at": now,
        "updated_at": now,
    }).execute()
    _log_action(user_id, LogAction.clone_vm, vm["name"], LogStatus.success, f"→ {new_name}")
    return _vm_row_to_response(inserted.data[0])


def export_ova(vm_id: str, output_path: str, user_id: str) -> dict:
    vm = _get_vm_or_404(vm_id, user_id)
    if vm["status"] != "stopped":
        raise HTTPException(
            status_code=409,
            detail=f"Cannot export VM in '{vm['status']}' state (must be stopped)",
        )

    vbox = build_vbox_path()
    try:
        result = run_vbox_command([vbox, "export", vm["name"], "--output", output_path], timeout=300)
    except FileNotFoundError:
        _log_action(user_id, LogAction.export_vm, vm["name"], LogStatus.failure, "VBoxManage not reachable")
        raise HTTPException(status_code=503, detail="VBoxManage not reachable") from None
    except subprocess.TimeoutExpired:
        _log_action(user_id, LogAction.export_vm, vm["name"], LogStatus.failure, "Export timed out")
        raise HTTPException(status_code=500, detail="Export timed out") from None

    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip()
        _log_action(user_id, LogAction.export_vm, vm["name"], LogStatus.failure, stderr)
        raise HTTPException(status_code=500, detail=f"VBoxManage export failed: {stderr}")

    _log_action(user_id, LogAction.export_vm, vm["name"], LogStatus.success, output_path)
    return {"message": f"Exported to {output_path}"}


def import_ova(source_path: str, name: str, ram: int, cpu: int, user_id: str) -> VMResponse:
    supabase = get_supabase_client()

    count_result = (
        supabase.table("vms").select("id", count="exact").eq("user_id", user_id).execute()
    )
    if (count_result.count or 0) >= settings.VM_QUOTA_PER_USER:
        raise HTTPException(
            status_code=409,
            detail=f"VM quota reached — maximum {settings.VM_QUOTA_PER_USER} VMs per user",
        )
    _check_disk_quota(user_id, 20480)

    name_check = (
        supabase.table("vms").select("id").eq("user_id", user_id).eq("name", name).execute()
    )
    if name_check.data:
        raise HTTPException(status_code=409, detail=f"A VM named '{name}' already exists")

    vbox = build_vbox_path()
    try:
        result = run_vbox_command(
            [vbox, "import", source_path, "--vsys", "0",
             "--vmname", name, "--memory", str(ram), "--cpus", str(cpu)],
            timeout=300,
        )
    except FileNotFoundError:
        _log_action(user_id, LogAction.import_vm, name, LogStatus.failure, "VBoxManage not reachable")
        raise HTTPException(status_code=503, detail="VBoxManage not reachable") from None
    except subprocess.TimeoutExpired:
        _log_action(user_id, LogAction.import_vm, name, LogStatus.failure, "Import timed out")
        raise HTTPException(status_code=500, detail="Import timed out") from None

    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip()
        _log_action(user_id, LogAction.import_vm, name, LogStatus.failure, stderr)
        raise HTTPException(status_code=500, detail=f"VBoxManage import failed: {stderr}")

    vbox_id: str | None = None
    info = run_vbox_command([vbox, "showvminfo", name, "--machinereadable"])
    if info.returncode == 0:
        for line in info.stdout.splitlines():
            if line.startswith("UUID="):
                vbox_id = line.split("=", 1)[1].strip('"')
                break

    now = datetime.now(timezone.utc).isoformat()
    inserted = supabase.table("vms").insert({
        "user_id": user_id,
        "name": name,
        "os": "imported",
        "ram": ram,
        "cpu": cpu,
        "disk_size": 20480,
        "status": "stopped",
        "vbox_id": vbox_id,
        "created_at": now,
        "updated_at": now,
    }).execute()
    _log_action(user_id, LogAction.import_vm, name, LogStatus.success, source_path)
    return _vm_row_to_response(inserted.data[0])


def get_vm_metrics(vm_id: str, user_id: str) -> dict:
    vm = _get_vm_or_404(vm_id, user_id)
    if vm["status"] != "running":
        raise HTTPException(status_code=409, detail="Metrics are only available for running VMs")

    vbox = build_vbox_path()
    vm_name = vm["name"]

    try:
        run_vbox_command(
            [vbox, "metrics", "setup", "--period", "1", "--samples", "1",
             vm_name, "CPU/Load/User,RAM/Usage/Used"],
        )
        result = run_vbox_command(
            [vbox, "metrics", "query", vm_name, "CPU/Load/User,RAM/Usage/Used"],
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, ValueError):
        return {"cpu_percent": None, "ram_used_mb": None}

    if result.returncode != 0:
        return {"cpu_percent": None, "ram_used_mb": None}

    cpu_percent: float | None = None
    ram_used_mb: int | None = None

    cpu_m = re.search(r"CPU/Load/User\s+([\d.]+)\s*%", result.stdout)
    if cpu_m:
        cpu_percent = float(cpu_m.group(1))

    ram_m = re.search(r"RAM/Usage/Used\s+([\d]+)\s+MB", result.stdout)
    if ram_m:
        ram_used_mb = int(ram_m.group(1))

    return {"cpu_percent": cpu_percent, "ram_used_mb": ram_used_mb}
