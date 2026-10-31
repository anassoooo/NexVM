"""The agent's view of the VM system (ports and adapters).

VMBackend is what the planner and executor depend on. LiveBackend wraps vm_service and the
database; evals/fake_backend.py provides an in-memory version for tests and evaluations.
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Protocol

from fastapi import HTTPException
from pydantic import BaseModel

from app.agent.world import VMState, World
from app.config import settings
from app.db import get_supabase_client
from app.models.schemas import VMCreate
from app.services import vm_service
from app.services.vbox_wrapper import get_iso_dir, resolve_inside


class StepError(Exception):
    """A write step failed for real; the message is safe to show and to give the planner."""


class VMBackend(Protocol):
    def world(self, user_id: str) -> World: ...
    def metrics(self, user_id: str, vm: VMState) -> dict | None: ...
    def recent_activity(self, user_id: str, limit: int) -> list[dict]: ...
    def execute(self, user_id: str, tool: str, args: BaseModel, world: World) -> str: ...


# Statuses that finish each transition. While a start/stop command may still be running, a sync
# could read VirtualBox before the command takes effect (e.g. still "poweroff" while starting)
# and write the old state back, so only a finishing state is accepted until the command's
# timeout has passed.
COMPLETES = {"starting": ("running", "paused"), "stopping": ("stopped",)}
IN_FLIGHT_SECONDS = 60  # run_vbox_command's default timeout

log = logging.getLogger(__name__)


def _status_value(status) -> str:
    return getattr(status, "value", status)


def _in_flight(row: dict) -> bool:
    try:
        changed = datetime.fromisoformat(row["updated_at"])
    except (KeyError, TypeError, ValueError):
        return False
    return (datetime.now(timezone.utc) - changed).total_seconds() < IN_FLIGHT_SECONDS


def _sync_transitional(row: dict, user_id: str) -> str:
    """start/stop leave "starting"/"stopping" until someone syncs with VirtualBox (the VMs page
    polls for it). Sync here, or the agent would see a VM stuck mid-transition."""
    accept = COMPLETES[row["status"]] if _in_flight(row) else None
    try:
        return _status_value(vm_service.sync_vm_status(row["id"], user_id, accept=accept).status)
    except Exception:  # one VM's sync must not block planning for the others
        log.warning("Could not sync VM %s; keeping status %r", row["id"], row["status"], exc_info=True)
        return row["status"]


def _rules(raw) -> list[dict]:
    if isinstance(raw, str):
        raw = json.loads(raw)
    return raw or []


class LiveBackend:
    def world(self, user_id: str) -> World:
        sb = get_supabase_client()
        rows = sb.table("vms").select("*").eq("user_id", user_id).execute().data or []
        for r in rows:
            if r["status"] in COMPLETES:
                r["status"] = _sync_transitional(r, user_id)
        snaps: dict[str, list[str]] = {}
        if rows:
            ids = [r["id"] for r in rows]
            for s in sb.table("vm_snapshots").select("vm_id,name").in_("vm_id", ids).execute().data or []:
                snaps.setdefault(s["vm_id"], []).append(s["name"])
        vms = {
            r["name"]: VMState(
                name=r["name"], status=r["status"], os=r["os"], ram=r["ram"], cpu=r["cpu"],
                disk_size=r["disk_size"], id=r["id"], iso_attached=bool(r.get("iso_path")),
                nat_rules=_rules(r.get("nat_rules")), vrde_port=r.get("vrde_port"),
                error_message=r.get("error_message"), snapshots=snaps.get(r["id"], []),
            )
            for r in rows
        }
        iso_dir = get_iso_dir()
        isos = sorted(f for f in os.listdir(iso_dir) if f.lower().endswith(".iso")) if os.path.isdir(iso_dir) else []
        return World(vms=vms, max_vms=settings.VM_QUOTA_PER_USER, disk_quota_mb=settings.VM_DISK_QUOTA_MB,
                     ports_in_use=vm_service._host_ports_in_use(), isos=isos)

    def metrics(self, user_id: str, vm: VMState) -> dict | None:
        if vm.status != "running" or not vm.id:
            return None
        try:
            return vm_service.get_vm_metrics(vm.id, user_id)
        except HTTPException:
            return None

    def recent_activity(self, user_id: str, limit: int) -> list[dict]:
        rows = (
            get_supabase_client().table("logs").select("action,target,status,message,created_at")
            .eq("user_id", user_id).order("created_at", desc=True).limit(limit).execute().data
        )
        return rows or []

    def execute(self, user_id: str, tool: str, args: BaseModel, world: World) -> str:
        a = args
        vm_id = world.get(a.vm).id if hasattr(a, "vm") else None
        try:
            match tool:
                case "create_vm":
                    vm = vm_service.create_vm(
                        VMCreate(name=a.name, os=a.os, ram=a.ram, cpu=a.cpu, disk_size=a.disk_size), user_id
                    )
                    return f"created '{vm.name}'"
                case "start_vm":
                    return _done(vm_service.start_vm(vm_id, user_id))
                case "stop_vm":
                    return _done(vm_service.stop_vm(vm_id, user_id))
                case "pause_vm":
                    return _done(vm_service.pause_vm(vm_id, user_id))
                case "resume_vm":
                    return _done(vm_service.resume_vm(vm_id, user_id))
                case "modify_vm":
                    vm = vm_service.modify_vm(vm_id, a.ram, a.cpu, user_id)
                    return f"'{vm.name}' now has {vm.ram} MB RAM, {vm.cpu} vCPU"
                case "delete_vm":
                    vm_service.delete_vm(vm_id, user_id)
                    return f"deleted '{a.vm}'"
                case "take_snapshot":
                    vm_service.take_snapshot(vm_id, a.snapshot, a.description, user_id)
                    return f"snapshot '{a.snapshot}' taken"
                case "restore_snapshot":
                    return _done(vm_service.restore_snapshot(vm_id, a.snapshot, user_id))
                case "add_port_rule":
                    vm_service.add_port_rule(vm_id, a.rule_name, a.protocol, a.host_port, a.guest_port, user_id)
                    return f"host port {a.host_port} → guest {a.guest_port}"
                case "clone_vm":
                    return f"created '{vm_service.clone_vm(vm_id, a.new_name, user_id).name}'"
                case "attach_iso":
                    path = resolve_inside(os.path.join(get_iso_dir(), a.iso_file), get_iso_dir())
                    return _done(vm_service.attach_iso(vm_id, path, user_id))
                case "detach_iso":
                    return _done(vm_service.detach_iso(vm_id, user_id))
        except HTTPException as exc:
            raise StepError(str(exc.detail)) from None
        except ValueError as exc:
            raise StepError(str(exc)) from None
        raise StepError(f"'{tool}' is not executable")


def _done(vm) -> str:
    return f"'{vm.name}' is {getattr(vm.status, 'value', vm.status)}"
