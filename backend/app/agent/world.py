"""World model and plan simulator.

A World is a snapshot of one user's VMs plus the host facts a plan depends on (quota, ports
in use, ISO files). The Simulator applies plan steps to a copy of it, enforcing the same state
rules as vm_service, so invalid plans are caught before the user ever sees them.
"""

import copy
from dataclasses import dataclass, field

from pydantic import BaseModel

from app.agent import tools as t


class SimulationError(Exception):
    pass


@dataclass
class VMState:
    name: str
    status: str
    os: str
    ram: int
    cpu: int
    disk_size: int
    id: str | None = None  # None for VMs that only exist in the plan so far
    iso_attached: bool = False
    nat_rules: list[dict] = field(default_factory=list)
    vrde_port: int | None = None
    error_message: str | None = None
    snapshots: list[str] = field(default_factory=list)

    def public(self) -> dict:
        return {
            "name": self.name, "status": self.status, "os": self.os, "ram_mb": self.ram,
            "cpu": self.cpu, "disk_mb": self.disk_size, "iso_attached": self.iso_attached,
            "port_rules": [f"{r['name']}: host {r['host_port']} -> guest {r['guest_port']}/{r['protocol']}"
                           for r in self.nat_rules],
            "snapshots": self.snapshots,
            **({"error": self.error_message} if self.error_message else {}),
        }


@dataclass
class World:
    vms: dict[str, VMState]
    max_vms: int
    disk_quota_mb: int
    ports_in_use: set[int] = field(default_factory=set)  # every VM on the host, all users
    isos: list[str] = field(default_factory=list)

    @property
    def disk_used_mb(self) -> int:
        return sum(vm.disk_size for vm in self.vms.values())

    def quota(self) -> dict:
        return {"vms_used": len(self.vms), "vms_limit": self.max_vms,
                "disk_used_mb": self.disk_used_mb, "disk_limit_mb": self.disk_quota_mb}

    def get(self, name: str) -> VMState:
        vm = self.vms.get(name)
        if vm is None:
            known = ", ".join(sorted(self.vms)) or "none"
            raise SimulationError(f"No VM named '{name}'. Existing VMs: {known}")
        return vm


def _require(vm: VMState, allowed: tuple[str, ...], action: str) -> None:
    if vm.status not in allowed:
        raise SimulationError(
            f"Cannot {action} '{vm.name}': it is {vm.status} (needs {' or '.join(allowed)})"
        )


def _check_capacity(world: World, extra_disk: int) -> None:
    if len(world.vms) >= world.max_vms:
        raise SimulationError(f"VM quota reached ({world.max_vms} VMs)")
    if world.disk_used_mb + extra_disk > world.disk_quota_mb:
        raise SimulationError(
            f"Disk quota exceeded: {world.disk_used_mb + extra_disk} MB needed, limit {world.disk_quota_mb} MB"
        )


def _new_name(world: World, name: str) -> None:
    vm = world.vms.get(name)
    if vm is not None and vm.id is None:
        raise SimulationError(
            f"'{name}' is already created by an earlier step of this plan. Do not create it again; "
            "continue with the next step"
        )
    if vm is not None:
        raise SimulationError(f"A VM named '{name}' already exists")


class Simulator:
    """Applies validated steps to its own copy of the world."""

    def __init__(self, world: World):
        self.world = copy.deepcopy(world)

    def apply(self, tool: str, args: BaseModel) -> str:
        """Apply one write step; return its simulated effect or raise SimulationError."""
        w = self.world
        a = args
        match tool:
            case "create_vm":
                _new_name(w, a.name)
                _check_capacity(w, a.disk_size)
                w.vms[a.name] = VMState(a.name, "stopped", a.os, a.ram, a.cpu, a.disk_size)
                return f"'{a.name}' will exist (stopped)"
            case "clone_vm":
                src = w.get(a.vm)
                _require(src, ("stopped", "error"), "clone")
                _new_name(w, a.new_name)
                _check_capacity(w, src.disk_size)
                w.vms[a.new_name] = VMState(a.new_name, "stopped", src.os, src.ram, src.cpu, src.disk_size)
                return f"'{a.new_name}' will exist (stopped copy of '{src.name}')"
            case "start_vm":
                vm = w.get(a.vm)
                _require(vm, ("stopped", "error"), "start")
                vm.status, vm.error_message = "running", None
            case "stop_vm":
                vm = w.get(a.vm)
                _require(vm, ("running",), "power off")
                vm.status = "stopped"
            case "pause_vm":
                vm = w.get(a.vm)
                _require(vm, ("running",), "pause")
                vm.status = "paused"
            case "resume_vm":
                vm = w.get(a.vm)
                _require(vm, ("paused",), "resume")
                vm.status = "running"
            case "modify_vm":
                vm = w.get(a.vm)
                _require(vm, ("stopped",), "resize")
                vm.ram = a.ram or vm.ram
                vm.cpu = a.cpu or vm.cpu
                return f"'{vm.name}' will have {vm.ram} MB RAM, {vm.cpu} vCPU"
            case "delete_vm":
                vm = w.get(a.vm)
                _require(vm, ("stopped", "error"), "delete")
                for r in vm.nat_rules:
                    w.ports_in_use.discard(int(r["host_port"]))
                del w.vms[vm.name]
                return f"'{vm.name}' and its disk will be gone"
            case "take_snapshot":
                vm = w.get(a.vm)
                _require(vm, ("stopped",), "snapshot")
                if a.snapshot in vm.snapshots:
                    raise SimulationError(f"'{vm.name}' already has a snapshot named '{a.snapshot}'")
                vm.snapshots.append(a.snapshot)
                return f"'{vm.name}' will have snapshot '{a.snapshot}'"
            case "restore_snapshot":
                vm = w.get(a.vm)
                _require(vm, ("stopped",), "restore")
                if a.snapshot not in vm.snapshots:
                    raise SimulationError(
                        f"'{vm.name}' has no snapshot '{a.snapshot}' (has: {', '.join(vm.snapshots) or 'none'})"
                    )
                return f"'{vm.name}' will be back at snapshot '{a.snapshot}'"
            case "add_port_rule":
                vm = w.get(a.vm)
                _require(vm, ("stopped",), "change port rules on")
                if any(r["name"] == a.rule_name for r in vm.nat_rules):
                    raise SimulationError(f"'{vm.name}' already has a port rule named '{a.rule_name}'")
                if a.host_port in w.ports_in_use:
                    free = next(p for p in range(a.host_port + 1, 65536) if p not in w.ports_in_use)
                    raise SimulationError(
                        f"Host port {a.host_port} is already in use. The next free port is {free}; "
                        "use it if the user did not insist on this exact port, otherwise ask them"
                    )
                w.ports_in_use.add(a.host_port)
                vm.nat_rules.append({"name": a.rule_name, "protocol": a.protocol,
                                     "host_port": a.host_port, "guest_port": a.guest_port})
                return f"host port {a.host_port} will reach '{vm.name}' port {a.guest_port}"
            case "attach_iso":
                vm = w.get(a.vm)
                _require(vm, ("stopped",), "attach an ISO to")
                if a.iso_file not in w.isos:
                    raise SimulationError(
                        f"No ISO named '{a.iso_file}' (available: {', '.join(w.isos) or 'none'})"
                    )
                vm.iso_attached = True
                return f"'{vm.name}' will boot from {a.iso_file}"
            case "detach_iso":
                vm = w.get(a.vm)
                _require(vm, ("stopped",), "detach the ISO from")
                if not vm.iso_attached:
                    raise SimulationError(f"'{vm.name}' has no ISO attached")
                vm.iso_attached = False
                return f"'{vm.name}' will boot from its disk"
            case _:
                raise SimulationError(f"'{tool}' is not a write tool")
        return f"'{a.vm}' will be {w.vms[a.vm].status}" if a.vm in w.vms else "ok"


def validate_args(tool: str, raw: dict) -> BaseModel:
    """Parse model-supplied arguments with the tool's Pydantic model (raises ValidationError)."""
    return t.TOOLS[tool].args.model_validate(raw)
