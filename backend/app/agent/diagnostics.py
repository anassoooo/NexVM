"""Deterministic VM health checks.

Findings come from rules, not from the model, so they are reproducible and testable; the
model's job is to explain them and, if useful, propose a fix as a normal plan.
"""

from dataclasses import asdict, dataclass

from app.agent.world import VMState, World

_RAM_PRESETS = (512, 1024, 2048, 4096, 8192, 16384)


@dataclass
class Finding:
    vm: str
    severity: str  # info | warning | critical
    code: str
    message: str
    suggestion: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def _next_ram(ram: int) -> int | None:
    return next((p for p in _RAM_PRESETS if p > ram), None)


def diagnose(vm: VMState, world: World, metrics: dict | None, activity: list[dict]) -> list[Finding]:
    found: list[Finding] = []

    if vm.status == "error":
        found.append(Finding(vm.name, "critical", "error_state",
                             f"VM is in error state: {vm.error_message or 'no details recorded'}",
                             "Start it again; if it keeps failing, check VirtualBox for the VM's log"))

    if vm.status in ("starting", "stopping"):
        found.append(Finding(vm.name, "warning", "transitional",
                             f"VM has been reported as '{vm.status}'",
                             "If it stays like this, an admin can force-reset it"))

    if metrics:
        used, cpu = metrics.get("ram_used_mb"), metrics.get("cpu_percent")
        if used is not None and vm.ram and used / vm.ram >= 0.9:
            bigger = _next_ram(vm.ram)
            found.append(Finding(vm.name, "warning", "memory_pressure",
                                 f"Guest RAM is {used} of {vm.ram} MB ({used * 100 // vm.ram}%)",
                                 f"Stop it and raise RAM to {bigger} MB" if bigger else "RAM is already at the maximum"))
        if cpu is not None and cpu >= 90:
            found.append(Finding(vm.name, "warning", "cpu_pressure", f"CPU load is {cpu:.0f}%",
                                 "Stop it and add vCPUs" if vm.cpu < 32 else "CPU is already at the maximum"))
    elif vm.status == "running":
        found.append(Finding(vm.name, "info", "no_metrics", "Live metrics are not available right now"))

    if vm.iso_attached:
        found.append(Finding(vm.name, "info", "iso_attached",
                             "An ISO is attached and the VM boots from it first",
                             "If the OS is already installed, detach the ISO so it boots from disk"))

    failures = [a for a in activity if a.get("target") == vm.name and a.get("status") == "failure"]
    if failures:
        last = failures[0]
        found.append(Finding(vm.name, "warning", "recent_failures",
                             f"{len(failures)} recent failed action(s); last: {last.get('action')} — {last.get('message')}"))

    if world.disk_quota_mb and world.disk_used_mb / world.disk_quota_mb >= 0.9:
        found.append(Finding(vm.name, "info", "disk_quota",
                             f"Disk quota {world.disk_used_mb} of {world.disk_quota_mb} MB used",
                             "Delete unused VMs before creating new ones"))

    if not found:
        found.append(Finding(vm.name, "info", "healthy", f"No problems found ({vm.status})"))
    return found
