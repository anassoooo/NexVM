# Research — Spec 006 P0 Bug Fixes

## No unknowns — all bugs are fully diagnosed

All five bugs are traceable to a single root cause: the `vm_service.list_vms()`
signature change (added required `user_id` parameter) was not propagated to all
call sites when it was introduced in the VM module completion task.

### B1 & B2 — `list_vms` call sites in ai_service.py

**Root cause**: `list_vms()` was refactored from no arguments to `list_vms(user_id: str)`.
Two call sites in `ai_service.py` were missed.

**Decision**: Pass the `user_id` already available in both contexts (`_build_system_prompt`
receives it; `_execute_action` receives it).

**No alternative needed** — straightforward propagation.

### B3 — AICreateVM schema / prompt missing cpu + disk_size

**Root cause**: `AICreateVM` was defined before `VMCreate` gained `cpu` and `disk_size`.
The schema was never updated.

**Decision**:
- Add `cpu: int = Field(ge=1, le=32, default=2)` to `AICreateVM`
- Add `disk_size: int = Field(ge=5120, le=512000, default=20480)` to `AICreateVM`
- Update system prompt `create_vm` example to show optional fields
- In `_execute_action`, pass `cpu=validated.get("cpu", 2)` and `disk_size=validated.get("disk_size", 20480)`

**Rationale**: Making them optional with defaults preserves backward compatibility —
users can still say "create a VM called foo" without specifying hardware.

### B4 — UUID vs str in admin_vm.py

**Root cause**: FastAPI/Pydantic deserializes `vm_id` as `uuid.UUID`. The service
layer was changed to `str` parameters but `admin_vm.py` was not updated (unlike
`vm.py` which already uses `str(body.vm_id)`).

**Decision**: Wrap with `str()`. No schema change needed.

### B5 — VM_STORAGE_PATH in .env

**Root cause**: New config field added to `config.py` but not documented in `.env`
or `.env.example`.

**Decision**: Add `VM_STORAGE_PATH=` (empty by default) to both files with a comment.

## Complexity Assessment

All fixes are surgical — no design decisions required. Total estimated effort: 30 min.
