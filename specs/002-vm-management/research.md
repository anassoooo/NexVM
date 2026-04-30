# Research: VM Management

**Branch**: `002-vm-management` | **Date**: 2026-04-06

---

## 1. VBoxManage Subprocess Wrapper

**Decision**: Wrap all VBoxManage calls in a single `run_vbox_command(cmd: list[str], timeout: int = 30)` function using `subprocess.run` with `capture_output=True`, `text=True`, and a fixed timeout. Never use `shell=True`.

**Rationale**: Passing commands as a list (not a string) prevents shell injection entirely — Python's subprocess module bypasses the shell when given a list. `capture_output=True` gives access to both stdout and stderr for error context. A 30-second timeout (FR-013) handles hung VMs without blocking the request indefinitely. Raising on non-zero `returncode` makes error handling uniform across all callers.

**Implementation pattern**:

```python
# services/vbox_wrapper.py
import subprocess

VBOXMANAGE_COMMANDS = {"createvm", "startvm", "controlvm", "unregistervm", "showvminfo"}

def run_vbox_command(cmd: list[str], timeout: int = 30) -> subprocess.CompletedProcess:
    if cmd[0] != settings.VBOXMANAGE_PATH:
        raise ValueError("First element must be VBOXMANAGE_PATH")
    if cmd[1] not in VBOXMANAGE_COMMANDS:
        raise ValueError(f"Subcommand '{cmd[1]}' is not whitelisted")
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
```

Callers check `result.returncode != 0` and treat it as a failure — no exception raised for non-zero exit, since VBoxManage uses exit codes (not exceptions) to signal errors.

**Handling `subprocess.TimeoutExpired`**: Callers wrap `run_vbox_command` in try/except for `subprocess.TimeoutExpired`. On timeout, set VM status to "error" with `error_message = "Command timed out"` and log the timeout.

**Alternatives considered**:
- `asyncio.create_subprocess_exec` — would allow non-blocking calls but introduces async subprocess complexity. Rejected for MVP; synchronous is sufficient with 30s timeout.
- `shell=True` with shlex.quote — technically safe with proper escaping but fundamentally riskier and harder to audit. Rejected.

---

## 2. VM State Machine Implementation

**Decision**: The service layer owns all state transitions. State is persisted in the `vms.status` column. The DB is updated **before** the VBoxManage call (to "starting"/"stopping") and again **after** (to "running"/"stopped"/"error").

**State transition table**:

| Current Status | Action  | Intermediate | Success       | Failure  |
|----------------|---------|--------------|---------------|----------|
| stopped        | start   | starting     | running       | error    |
| error          | start   | starting     | running       | error    |
| running        | stop    | stopping     | stopped       | error    |
| stopped        | delete  | (none)       | (record gone) | (no-op)  |

**Rationale for pre-updating status**: If the backend crashes after the VBoxManage call but before the DB update, the VM is in an inconsistent state either way. Pre-updating to "starting"/"stopping" ensures the DB at least reflects that an operation was attempted. This is preferable to claiming "stopped" when VBoxManage already fired. The error state + `error_message` field provides the admin recovery path.

**Concurrency guard**: Before any state transition, the service queries the current status. If the VM is already in a transitional state ("starting" or "stopping"), it returns HTTP 409 immediately. This is sufficient for single-tenant MVP — no database-level locking needed.

```python
# In vm_service.py
async def start_vm(vm_id: str, user_id: str) -> VMResponse:
    vm = await get_vm_or_404(vm_id, user_id)
    if vm["status"] in ("starting", "stopping"):
        raise HTTPException(409, "VM is already in a transitional state")
    if vm["status"] not in ("stopped", "error"):
        raise HTTPException(409, f"Cannot start VM in '{vm['status']}' state")
    
    # Pre-update before subprocess
    await update_vm_status(vm_id, "starting", error_message=None)
    
    try:
        result = run_vbox_command([settings.VBOXMANAGE_PATH, "startvm", vm["name"], "--type", "headless"])
        if result.returncode != 0:
            await update_vm_status(vm_id, "error", error_message=result.stderr)
            raise HTTPException(500, f"VBoxManage failed: {result.stderr}")
        await update_vm_status(vm_id, "running", error_message=None)
    except subprocess.TimeoutExpired:
        await update_vm_status(vm_id, "error", error_message="Command timed out")
        raise HTTPException(500, "VBoxManage command timed out")
    
    await log_action(user_id, "start_vm", vm_id, "success", "VM started")
    return await get_vm(vm_id, user_id)
```

**Alternatives considered**:
- Database advisory locks — more correct for multi-tenant/distributed, but overengineered for single-tenant MVP. Rejected.
- Background task queue (Celery/ARQ) — decouples subprocess from HTTP, allows real-time status polling. Correct long-term architecture; deferred to post-MVP.

---

## 3. Create VM: DB Record Lifecycle

**Decision**: For creation, attempt VBoxManage first. Only insert the DB record after VBoxManage succeeds. If VBoxManage fails, no record is created and the error is logged without a VM ID target (use literal "create_vm" as target).

**Rationale**: The inverse order (DB first, VBoxManage second) would leave orphaned DB records on VBoxManage failure and require compensating deletes. Since creating the DB record is cheap and reversible, waiting for VBoxManage success is cleaner. FR-002 requires exactly this: "If VBoxManage fails, no DB record is created."

**For delete**: VBoxManage first, then DB delete. Same rationale — the DB record is the system's reference; removing it before VBoxManage would lose the VM name needed to call unregistervm.

---

## 4. Logging Before Response

**Decision**: Insert the log record unconditionally — for both successes and failures — before the final `return` or `raise HTTPException`.

**Rationale**: Constitution §12.1 and spec FR-014 both require logging before the response. This ensures no action goes unlogged even if a subsequent serialization step fails. The log call uses the supabase service-role client to bypass RLS (since it writes on behalf of the user, not as the user).

```python
async def log_action(user_id: str, action: str, target: str, status: str, message: str):
    supabase_service.table("logs").insert({
        "user_id": user_id,
        "action":  action,
        "target":  target,
        "status":  status,
        "message": message,
    }).execute()
```

**Failure behavior**: If the log insert itself fails (e.g., DB unavailable), the exception is caught and printed to stderr — it does NOT block the main operation's response. Logging failures must not cascade into operation failures.

---

## 5. Frontend: Refetch Strategy

**Decision**: The frontend refetches the full VM list from `GET /api/v1/vm` after every mutation (create, start, stop, delete). No optimistic updates. No polling.

**Rationale**: Optimistic updates require rollback logic when VBoxManage fails — adding complexity that is not justified for MVP. Polling would add unnecessary load and complication. Since VBoxManage calls are synchronous and the response only returns after the operation completes, a single refetch after the response is sufficient to show the updated state.

**Pattern in React**:
```typescript
const handleStart = async (vmId: string) => {
  setLoading(vmId)
  try {
    await apiClient.post(`/vm/start`, { vm_id: vmId })
  } finally {
    await refetchVMs()   // always refetch, even on error
    setLoading(null)
  }
}
```

**Alternatives considered**:
- Real-time subscription via Supabase Realtime — correct for multi-user; deferred post-MVP.
- Optimistic UI (update local state immediately) — requires error rollback; rejected for MVP.

---

## 6. VM Name Validation

**Decision**: Validate at two layers — Pydantic regex at the API boundary and a note in the VirtualBox wrapper that names are passed as list args (never interpolated).

**Pydantic field validator**:
```python
from pydantic import BaseModel, field_validator
import re

class VMCreate(BaseModel):
    name: str
    os: str
    ram: int

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9 \-]{0,49}", v):
            raise ValueError("Name must be 1–50 chars: alphanumeric, hyphens, spaces")
        return v

    @field_validator("ram")
    @classmethod
    def validate_ram(cls, v: int) -> int:
        if not (512 <= v <= 16384):
            raise ValueError("RAM must be between 512 and 16384 MB")
        return v
```

**Rationale**: Regex prevents names that would cause problems in log messages or future display contexts. The subprocess list-argument approach means validation is defense-in-depth, not the primary security control — but it is still required for data quality (FR-016).

---

## 7. 404 vs 403 for Cross-User Access

**Decision**: Return 404 (not 403) when a user attempts to act on another user's VM.

**Rationale**: Returning 403 leaks the existence of the VM. Returning 404 does not reveal whether the VM exists at all — consistent with FR-015 ("Requests targeting another user's VM MUST return HTTP 404"). RLS in Supabase naturally returns an empty result for cross-user queries; the service layer interprets an empty result as "not found" and raises 404.

```python
async def get_vm_or_404(vm_id: str, user_id: str) -> dict:
    result = supabase.table("vms").select("*").eq("id", vm_id).eq("user_id", user_id).execute()
    if not result.data:
        raise HTTPException(404, "VM not found")
    return result.data[0]
```
