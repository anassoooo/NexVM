"""In-memory VMBackend for tests and evals: same rules as the simulator, no VirtualBox or DB."""

import copy
import uuid

from pydantic import BaseModel

from app.agent.backend import StepError
from app.agent.world import SimulationError, Simulator, VMState, World


def make_world(vms: list[dict] | None = None, *, max_vms: int = 5, disk_quota_mb: int = 200000,
               ports_in_use: set[int] | None = None, isos: list[str] | None = None) -> World:
    states = {}
    for v in vms or []:
        v = {"os": "Ubuntu 22.04", "ram": 2048, "cpu": 2, "disk_size": 20480, "status": "stopped", **v}
        states[v["name"]] = VMState(id=v.pop("id", str(uuid.uuid4())), **v)
    return World(vms=states, max_vms=max_vms, disk_quota_mb=disk_quota_mb,
                 ports_in_use=set(ports_in_use or ()), isos=list(isos or []))


class FakeBackend:
    def __init__(self, world: World, *, metrics: dict[str, dict] | None = None,
                 activity: list[dict] | None = None, failures: dict[str, str] | None = None):
        self._world = world
        self._metrics = metrics or {}
        self._activity = activity or []
        # "tool" or "tool:vm" -> error message; consumed once so a repaired plan can succeed
        self.failures = dict(failures or {})
        self.executed: list[tuple[str, dict]] = []

    def world(self, user_id: str) -> World:
        return copy.deepcopy(self._world)

    def metrics(self, user_id: str, vm: VMState) -> dict | None:
        return self._metrics.get(vm.name) if vm.status == "running" else None

    def recent_activity(self, user_id: str, limit: int) -> list[dict]:
        return self._activity[:limit]

    def execute(self, user_id: str, tool: str, args: BaseModel, world: World) -> str:
        target = getattr(args, "vm", None) or getattr(args, "name", None)
        for key in (f"{tool}:{target}", tool):
            if key in self.failures:
                raise StepError(self.failures.pop(key))
        sim = Simulator(self._world)
        try:
            effect = sim.apply(tool, args)
        except SimulationError as exc:
            raise StepError(str(exc)) from None
        for vm in sim.world.vms.values():
            vm.id = vm.id or str(uuid.uuid4())
        self._world = sim.world
        self.executed.append((tool, args.model_dump()))
        return effect.replace(" will be", " is").replace(" will ", " ")
