# Tasks: VM Management

**Input**: Design documents from `/specs/002-vm-management/`  
**Prerequisites**: `001-supabase-auth-db` complete ✅ — auth middleware, schema (vms + logs tables), RLS, Pydantic schemas (VMCreate, VMResponse), enums (VMStatus, LogAction) all in place.

**Tests**: Backend unit tests for vm_service.py with mocked VBoxManage subprocess.

**Organization**: Tasks are grouped by layer. Backend foundation must be complete before frontend integration.

## Format: `[ID] [P?] Description`

- **[P]**: Can run in parallel (different files, no shared dependencies)

---

## Phase 1: Backend Foundation

**Purpose**: Implement the VBoxManage wrapper, VM service layer, and HTTP routes. No frontend work until this phase is complete and tested.

- [x] T001 Create `backend/app/services/vbox_wrapper.py` — `VBOXMANAGE_COMMANDS` whitelist set; `run_vbox_command(cmd: list[str], timeout: int = 30) -> subprocess.CompletedProcess`: assert `cmd[1]` is in whitelist, call `subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)`, return result; callers handle non-zero returncode and `TimeoutExpired`

- [x] T002 Create `backend/app/services/vm_service.py` — implement these six functions using the supabase **service role client** for all DB writes, and `get_current_user`-provided `user_id` for ownership filtering:
  - `list_vms(user_id) -> list[VMResponse]`: SELECT all vms WHERE user_id = user_id
  - `get_vm_status(vm_id, user_id) -> VMResponse`: SELECT vms WHERE id = vm_id AND user_id = user_id; raise 404 if empty
  - `create_vm(data: VMCreate, user_id) -> VMResponse`: call VBoxManage createvm → INSERT vms with status='stopped' → log create_vm success/failure; raise 409 on name conflict (VBoxManage exit code with "already exists" in stderr); raise 503 if VBoxManage binary not found
  - `start_vm(vm_id, user_id) -> VMResponse`: get_vm_or_404 → check state (409 if transitional, 409 if not stopped/error) → UPDATE status='starting' → VBoxManage startvm → UPDATE status='running' (success) or 'error' with stderr (failure) → log start_vm
  - `stop_vm(vm_id, user_id) -> VMResponse`: get_vm_or_404 → check state (409 if transitional, 409 if not running) → UPDATE status='stopping' → VBoxManage controlvm poweroff → UPDATE status='stopped' or 'error' → log stop_vm
  - `delete_vm(vm_id, user_id)`: get_vm_or_404 → check status='stopped' (409 if not) → VBoxManage unregistervm --delete → DELETE vms record → log delete_vm; on VBoxManage failure do NOT delete DB record

- [x] T003 Add `VMActionRequest` to `backend/app/models/schemas.py` — `vm_id: str` field; no other changes to this file

- [x] T004 Create `backend/app/routes/vm.py` — HTTP layer only, no business logic; import and call vm_service functions; all routes take `current_user_id: str = Depends(get_current_user)`:
  - `GET  /` → `list_vms` → 200
  - `POST /status` → `get_vm_status` → 200
  - `POST /create` → `create_vm` → 201
  - `POST /start` → `start_vm` → 200
  - `POST /stop` → `stop_vm` → 200
  - `POST /delete` → `delete_vm` → 200 `{"detail": "VM deleted"}`

- [x] T005 Update `backend/app/main.py` — include the VM router: `app.include_router(vm_router, prefix="/api/v1/vm", tags=["vm"])`

**Checkpoint**: `uvicorn app.main:app --reload` starts without errors. `GET /api/v1/health` still returns 200. All 6 VM routes appear in `/docs`.

---

## Phase 2: Backend Tests

**Purpose**: Verify all state transitions and DB write sequences using mocked VBoxManage.

- [x] T006 Create `backend/tests/test_vm_service.py` — use `pytest` + `unittest.mock.patch("app.services.vbox_wrapper.subprocess.run")`; test these cases:

  **create_vm**:
  - (1) VBoxManage returns exit 0 → VM record inserted with status='stopped', log created with action='create_vm' status='success'
  - (2) VBoxManage returns non-zero with "already exists" in stderr → 409 raised, no DB record created
  - (3) VBoxManage returns non-zero (generic failure) → 500 raised, no DB record created, log created with status='failure'

  **start_vm**:
  - (4) VM in 'stopped' + VBoxManage exit 0 → status transitions: stopped → starting → running, log='success'
  - (5) VM in 'error' + VBoxManage exit 0 → same transitions as (4), error_message cleared
  - (6) VM in 'running' → 409 raised before any VBoxManage call
  - (7) VM in 'starting' → 409 raised before any VBoxManage call
  - (8) VM in 'stopped' + VBoxManage exit non-zero → status='error', error_message=stderr, log='failure'
  - (9) VM in 'stopped' + VBoxManage raises TimeoutExpired → status='error', error_message='Command timed out', log='failure'

  **stop_vm**:
  - (10) VM in 'running' + VBoxManage exit 0 → status transitions: running → stopping → stopped, log='success'
  - (11) VM in 'stopped' → 409 raised before any VBoxManage call
  - (12) VM in 'running' + VBoxManage exit non-zero → status='error', error_message=stderr, log='failure'

  **delete_vm**:
  - (13) VM in 'stopped' + VBoxManage exit 0 → DB record deleted, log='success'
  - (14) VM in 'running' → 409 raised before any VBoxManage call
  - (15) VM in 'stopped' + VBoxManage exit non-zero → DB record NOT deleted, log='failure', 500 raised

  **get_vm_or_404**:
  - (16) vm_id exists with correct user_id → returns VM dict
  - (17) vm_id exists with wrong user_id → 404 raised (cross-user isolation)
  - (18) vm_id does not exist → 404 raised

**Checkpoint**: `pytest backend/tests/test_vm_service.py -v` — all 18 cases pass.

---

## Phase 3: Frontend

**Purpose**: VM list page and interactive VM cards. Depends on Phase 1 backend being runnable.

- [x] T007 [P] Create `frontend/components/vm-card.tsx` — client component; props: `vm: VM, onStart, onStop, onDelete, loading: boolean`; renders: VM name (bold), OS label, RAM in MB, status badge (color-coded: green=running, grey=stopped, amber=starting/stopping, red=error), error_message text when status='error'; Start/Stop/Delete buttons disabled when `loading=true` OR VM status is 'starting'/'stopping'; Start enabled only when status is 'stopped'/'error'; Stop enabled only when 'running'; Delete enabled only when 'stopped'

- [x] T008 [P] Create `frontend/components/vm-list.tsx` — client component; props: `vms: VM[], loading: boolean, onRefetch: () => void`; renders VMCard for each VM; shows loading skeleton (3 placeholder cards) when `loading=true`; shows empty state "No VMs yet — create your first one" when `vms.length === 0`; passes action handlers that call API and then call `onRefetch`

- [x] T009 Create `frontend/app/vms/page.tsx` — server component; reads session via `createServerClient`; fetches initial VM list via `GET /api/v1/vm` with JWT; passes to a `VMListClient` client wrapper; includes a "Create VM" button that opens a modal form (inline form for MVP — no separate route)

- [x] T010 Create `frontend/components/vm-create-form.tsx` — client component; form fields: name (text, max 50), OS (text), RAM (number 512–16384); Zod schema matching FR-001 validation (same rules as backend); on submit calls `POST /api/v1/vm/create` via `lib/api.ts`; on success closes form and triggers refetch; on error displays `detail` from error response

- [x] T011 [P] Update `frontend/app/dashboard/page.tsx` — add "VMs" navigation link pointing to `/vms`

- [x] T012 [P] Update `frontend/components/navbar.tsx` (or root layout navbar stub) — add "VMs" nav item

**Checkpoint**: `/vms` loads, empty state shown. Create VM form submits, VM appears. Start/Stop/Delete buttons work. Transitional state disables buttons correctly.

---

## Phase 4: Integration Validation

- [x] T013 Run every step in `specs/002-vm-management/quickstart.md` and verify all 11 smoke tests pass. Fix any gaps found.

---

## Dependencies & Execution Order

```text
Phase 1 (Backend Foundation)
    ↓
Phase 2 (Backend Tests) ← can overlap with Phase 3 once T001–T002 are done
    ↓
Phase 3 (Frontend) ← requires Phase 1 backend running for API calls
    ↓
Phase 4 (Integration Validation)
```

### Within Phase 1

```
T001 (vbox_wrapper) → T002 (vm_service) → T003 [P] + T004 [P] → T005
```

T002 depends on T001. T003 and T004 are independent of each other. T005 depends on T004.

### Within Phase 3

```
T007 [P] + T008 [P] → T009 → T010 → T011 [P] + T012 [P]
```

T007 and T008 are independent components. T009 composes them. T010 is a separate form component used by T009.

---

## Parallel Opportunities

### Phase 1 (2 parallel streams after T002)

```
Stream A: T001 → T002 → T004 → T005
Stream B: T003 (schemas.py update — independent file)
```

### Phase 3 (2 parallel streams)

```
Stream A: T007 + T008 → T009 → T010
Stream B: T011 + T012 (layout/nav updates — independent)
```

---

## Notes

- **T002** is the most critical task — all state machine logic lives here. Write it carefully; T006 tests every branch.
- **T001** must be complete before T002 — the service calls the wrapper.
- **No new migrations** — do not modify `supabase/migrations/`. The schema from spec 001 is complete.
- **Service role key** — vm_service.py must use `SUPABASE_SERVICE_KEY` (not the anon key) for all DB writes, to bypass RLS. The `user_id` filter in queries is the authorization control.
- **Log before return** — every function in vm_service.py must call `log_action` before its final `return` or `raise`.
- Commit after Phase 2 checkpoint (`pytest` all green) and after Phase 4 checkpoint (full smoke test passes).
