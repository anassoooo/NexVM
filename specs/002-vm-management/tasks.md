# Tasks: VM Management

**Feature**: VM Management | **Branch**: `002-vm-management`
**Input**: Design documents from `/specs/002-vm-management/`
**Depends on**: `001-supabase-auth-db` complete (auth middleware, `vms` + `logs` tables, RLS, Pydantic schemas VMCreate/VMResponse, enums VMStatus/LogAction)

**Format**: `- [ ] T### [P?] [US?] Description with file path`
- **[P]**: Parallel-safe — no shared file dependencies, can run concurrently
- **[US#]**: Maps to User Story in spec.md

---

## Phase 1: Setup

**Purpose**: Branch creation and project scaffolding. No production code yet.

- [ ] T001 Create feature branch `002-vm-management` from `main` (or `001-supabase-auth-db` merge commit) and push to remote

- [ ] T002 Verify spec 001 dependencies are importable — confirm `backend/app/dependencies.py` exports `get_current_user` / `get_current_admin_user`, `backend/app/models/schemas.py` exports `VMCreate` / `VMResponse`, `backend/app/models/enums.py` exports `VMStatus` / `LogAction`; document any gaps

---

## Phase 2: Foundational

**Purpose**: VBoxManage subprocess wrapper, Pydantic schema addition, and logging helper. These are prerequisites for every user story.

- [ ] T003 Create `backend/app/services/vbox_wrapper.py` — define `VBOXMANAGE_COMMANDS` whitelist set (`createvm`, `startvm`, `controlvm`, `unregistervm`, `showvminfo`); implement `run_vbox_command(cmd: list[str], timeout: int = 30) -> subprocess.CompletedProcess` that validates `cmd[1]` against whitelist (raises `ValueError` on mismatch), calls `subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)`, returns result; define `VBOXMANAGE_PATH` from `os.environ.get("VBOXMANAGE_PATH", "VBoxManage")`; per contracts/vbox-commands.md

- [ ] T004 [P] Add `VMActionRequest` to `backend/app/models/schemas.py` — `vm_id: str` field; no other modifications to existing schemas

- [ ] T005 Create logging helper in `backend/app/services/vm_service.py` (or shared util) — `log_action(supabase, user_id, action, target, status, message)` that INSERTs into `logs` table using service role client; action values: `create_vm`, `start_vm`, `stop_vm`, `delete_vm`; per data-model.md logs table contract

---

## Phase 3: US1 — Create and Register a VM (P1)

**Purpose**: VM creation endpoint — VBoxManage createvm, DB insert, name conflict detection, input validation. Every other action requires an existing VM.

- [ ] T006 Implement `create_vm(data: VMCreate, user_id) -> VMResponse` in `backend/app/services/vm_service.py` — build command via `run_vbox_command([VBOXMANAGE_PATH, "createvm", "--name", name, "--register"])`; on success INSERT into `vms` with `status='stopped'`; on non-zero returncode check stderr for "already exists" → raise 409 `{"detail": "A VM with this name already exists"}` else raise 500 with stderr; on `TimeoutExpired` raise 500 `"VBoxManage command timed out"`; on `FileNotFoundError` raise 503 `"VBoxManage not reachable"`; log outcome before return; per FR-001 through FR-004, contracts/vm-api.md POST /vm/create

- [ ] T007 Implement `list_vms(user_id) -> list[VMResponse]` in `backend/app/services/vm_service.py` — SELECT from `vms` WHERE `user_id = user_id`; return empty list (not 404) when no rows; per FR-012, contracts/vm-api.md GET /vm

- [ ] T008 Implement `get_vm_or_404(vm_id, user_id=None)` helper in `backend/app/services/vm_service.py` — SELECT from `vms` WHERE `id = vm_id` (AND `user_id = user_id` if `user_id` is not None); raise HTTPException 404 `"VM not found"` if empty; used by all per-VM operations; per FR-015

- [ ] T009 Create `backend/app/routes/vm.py` — FastAPI `APIRouter(prefix="/api/v1/vm")`; create routes: `GET /` → `list_vms` (200), `POST /create` → `create_vm` (201); all routes depend on `get_current_user`; no business logic in route layer — delegate to vm_service

- [ ] T010 Update `backend/app/main.py` — `app.include_router(vm_router, prefix="/api/v1/vm", tags=["vm"])`; verify app starts without errors

**Checkpoint**: `POST /api/v1/vm/create` with valid payload returns 201, VM appears in `GET /api/v1/vm`. Duplicate name returns 409. Invalid payload returns 422.

---

## Phase 4: US2 — Start and Stop a VM (P1)

**Purpose**: Start/stop state transitions — intermediate states (`starting`/`stopping`), VBoxManage commands, error handling with retry from `error` state.

- [ ] T011 Implement `start_vm(vm_id, user_id=None) -> VMResponse` in `backend/app/services/vm_service.py` — call `get_vm_or_404`; reject with 409 if status is `starting` or `stopping`; reject with 409 if status not in `{stopped, error}`; UPDATE `status='starting'`; call `run_vbox_command([VBOXMANAGE_PATH, "startvm", name, "--type", "headless"])`; on success UPDATE `status='running'`, clear `error_message`; on failure UPDATE `status='error'`, set `error_message=stderr`; on `TimeoutExpired` UPDATE `status='error'`, `error_message='Command timed out'`; log outcome; per FR-005, FR-006, FR-009, FR-013

- [ ] T012 Implement `stop_vm(vm_id, user_id=None) -> VMResponse` in `backend/app/services/vm_service.py` — call `get_vm_or_404`; reject with 409 if status is `starting` or `stopping`; reject with 409 if status not `running`; UPDATE `status='stopping'`; call `run_vbox_command([VBOXMANAGE_PATH, "controlvm", name, "poweroff"])`; on success UPDATE `status='stopped'`; on failure UPDATE `status='error'`, set `error_message=stderr`; on `TimeoutExpired` UPDATE `status='error'`, `error_message='Command timed out'`; log outcome; per FR-007, FR-008, FR-009, FR-013

- [ ] T013 Implement `get_vm_status(vm_id, user_id) -> VMResponse` in `backend/app/services/vm_service.py` — call `get_vm_or_404`; return VMResponse; per contracts/vm-api.md POST /vm/status

- [ ] T014 Add start/stop/status routes to `backend/app/routes/vm.py` — `POST /start` → `start_vm` (200), `POST /stop` → `stop_vm` (200), `POST /status` → `get_vm_status` (200); all accept `VMActionRequest` body; per contracts/vm-api.md

**Checkpoint**: `POST /api/v1/vm/start` transitions stopped→starting→running. `POST /api/v1/vm/stop` transitions running→stopping→stopped. 409 on transitional states. Error state allows retry.

---

## Phase 5: US3 — Delete a VM (P2)

**Purpose**: VM deletion — VBoxManage unregistervm with `--delete`, stopped-state guard, DB record removal only on success.

- [ ] T015 Implement `delete_vm(vm_id, user_id=None)` in `backend/app/services/vm_service.py` — call `get_vm_or_404`; reject with 409 if status is not `stopped` (message: `"Cannot delete VM in '<status>' state — stop it first"`); call `run_vbox_command([VBOXMANAGE_PATH, "unregistervm", name, "--delete"])`; on success DELETE from `vms`; on failure do NOT delete DB record, raise 500; log outcome; per FR-010, FR-011

- [ ] T016 Add delete route to `backend/app/routes/vm.py` — `POST /delete` → `delete_vm`; returns `{"detail": "VM deleted"}` on success; per contracts/vm-api.md POST /vm/delete

**Checkpoint**: `POST /api/v1/vm/delete` on a stopped VM removes DB record. Returns 409 if VM is running/starting/stopping/error. VBoxManage failure preserves DB record.

---

## Phase 6: US4 — Admin VM List and Status (P1)

**Purpose**: Admin panel VM list showing all users' VMs with color-coded badges and full controls (start/stop/delete any VM).

- [ ] T017 Implement `list_all_vms() -> list[VMResponse]` in `backend/app/services/vm_service.py` — SELECT all from `vms` (no user_id filter); admin-only function; per FR-021

- [ ] T018 Create `backend/app/routes/admin_vm.py` — FastAPI `APIRouter`; all routes depend on `get_current_admin_user`; routes: `GET /` → `list_all_vms` (200), `POST /start` → `start_vm(vm_id, user_id=None)` (200), `POST /stop` → `stop_vm(vm_id, user_id=None)` (200), `POST /delete` → `delete_vm(vm_id, user_id=None)` (200); per FR-021

- [ ] T019 Update `backend/app/main.py` — `app.include_router(admin_vm_router, prefix="/api/v1/admin/vm", tags=["admin-vm"])`; verify app starts and admin routes appear in `/docs`

- [ ] T020 [P] Create `frontend/components/vm-card.tsx` — client component; props: `vm: VM & { ownerEmail?: string }, onStart, onStop, onDelete, loading: boolean`; renders: VM name (bold), OS label, RAM in MB, owner email (shown only when `ownerEmail` is present — admin view), status badge (green=`running`, grey=`stopped`, amber=`starting`/`stopping`, red=`error`), error_message text when `status='error'`; Start/Stop/Delete buttons disabled when `loading=true` OR status is `starting`/`stopping`; Start enabled for `stopped`/`error`; Stop enabled for `running`; Delete enabled for `stopped`; per FR-018, FR-019, FR-020

- [ ] T021 [P] Create `frontend/components/vm-list.tsx` — client component; props: `vms: VM[], loading: boolean, onRefetch: () => void, showOwner?: boolean`; renders VMCard for each VM; loading skeleton (3 placeholder cards) when `loading=true`; empty state `"No VMs in the system"` when `vms.length === 0`; action handlers call API then `onRefetch`; per FR-018

- [ ] T022 Create `frontend/app/admin/vms/page.tsx` — server component with admin guard (redirect non-admin to `/ai`); fetches VM list via `GET /api/v1/admin/vm` with JWT; renders VMList with `showOwner=true`; includes "Create VM" button opening modal form; action buttons call `/api/v1/admin/vm/*` endpoints; per FR-018, FR-021

- [ ] T023 Create `frontend/components/vm-create-form.tsx` — client component; form fields: name (text, max 50, alphanumeric+hyphens+spaces), OS (text, required), RAM (number 512–16384); Zod schema matching FR-001 validation; on submit calls `POST /api/v1/vm/create` via `lib/api.ts`; on success closes form and triggers refetch; on error displays `detail` from error response

**Checkpoint**: `/admin/vms` loads with all users' VMs. Status badges color-coded. Start/Stop/Delete work on any VM. Create VM form works. Non-admin redirected to `/ai`.

---

## Phase 7: Backend Tests

**Purpose**: Comprehensive mocked tests for all state transitions and error paths. Validates every acceptance scenario from the spec.

- [ ] T024 Create `backend/tests/test_vm_service.py` — use `pytest` + `unittest.mock.patch("app.services.vbox_wrapper.subprocess.run")`; test cases:

  **create_vm** (3 cases):
  - (1) VBoxManage exit 0 → VM inserted with `status='stopped'`, log `action='create_vm' status='success'`
  - (2) VBoxManage non-zero with "already exists" in stderr → 409 raised, no DB record
  - (3) VBoxManage non-zero (generic) → 500 raised, no DB record, log `status='failure'`

  **start_vm** (6 cases):
  - (4) `stopped` + VBoxManage exit 0 → transitions: stopped→starting→running, log success
  - (5) `error` + VBoxManage exit 0 → same transitions, `error_message` cleared
  - (6) `running` → 409, no VBoxManage call
  - (7) `starting` → 409, no VBoxManage call
  - (8) `stopped` + VBoxManage non-zero → `status='error'`, `error_message=stderr`, log failure
  - (9) `stopped` + TimeoutExpired → `status='error'`, `error_message='Command timed out'`, log failure

  **stop_vm** (3 cases):
  - (10) `running` + VBoxManage exit 0 → running→stopping→stopped, log success
  - (11) `stopped` → 409, no VBoxManage call
  - (12) `running` + VBoxManage non-zero → `status='error'`, `error_message=stderr`, log failure

  **delete_vm** (3 cases):
  - (13) `stopped` + VBoxManage exit 0 → DB record deleted, log success
  - (14) `running` → 409, no VBoxManage call
  - (15) `stopped` + VBoxManage non-zero → DB record preserved, log failure, 500 raised

  **get_vm_or_404** (3 cases):
  - (16) Correct user_id → returns VM dict
  - (17) Wrong user_id → 404 (cross-user isolation)
  - (18) Non-existent vm_id → 404

**Checkpoint**: `pytest backend/tests/test_vm_service.py -v` — all 18 cases pass.

---

## Phase 8: Polish

**Purpose**: Integration validation, edge-case hardening, final cleanup.

- [ ] T025 Run every step in `specs/002-vm-management/quickstart.md` and verify all smoke tests pass; fix any gaps found

- [ ] T026 Verify VBoxManage-not-installed edge case — confirm `POST /api/v1/vm/create` returns 503 `"VBoxManage not reachable"` when VBoxManage binary is absent (per spec edge case: VBoxManage not installed)

- [ ] T027 Verify concurrent start protection — confirm second start request on same VM returns 409 immediately when VM is already in `starting` state (per spec edge case: concurrent start on same VM)

- [ ] T028 Run `ruff check .` in `backend/` and fix all lint issues

- [ ] T029 Run `pytest` in `backend/` and confirm full test suite passes (including any existing tests from spec 001)

---

---

## Phase 9: Clarification Improvements (2026-04-20)

**Purpose**: Implement FR-022 (admin force-reset), add missing test coverage for FR-010 error-delete and FR-001 quota, and wire the Force Reset button in the admin UI. All other clarification changes (error_message in AI context, post-create warning, quota check, error-state delete) were already applied to code directly.

- [X] T030 Implement `force_reset_vm(vm_id: str, actor_id: str) -> VMResponse` in `backend/app/services/vm_service.py` — call `_get_vm_or_404(vm_id, user_id=None)` (no ownership check); UPDATE `vms` SET `status='stopped'`, `error_message=None`, `updated_at=now` WHERE `id=vm_id`; log action `LogAction.force_reset_vm` with `LogStatus.success`; return updated VMResponse; DB-only, no VBoxManage call; per FR-022

- [X] T031 Add `POST /force-reset` route to `backend/app/routes/admin_vm.py` — depends on `get_current_admin_user`; accepts `VMActionRequest` body; calls `vm_service.force_reset_vm(vm_id=body.vm_id, actor_id=current_user.id)`; returns 200 with updated `VMResponse`; per FR-022

- [X] T032 Add "Force Reset" button to `frontend/components/vm-card.tsx` — visible ONLY when `showOwner=true` (admin view) AND `vm.status` is `"starting"`, `"stopping"`, or `"error"`; on click calls `POST /api/v1/admin/vm/force-reset` with `{vm_id}`; disabled when `loading=true`; styled with `--warning` color (`#ff6d00`) to distinguish from Start/Stop/Delete; per FR-022

- [X] T033 [P] Add 3 test cases to `backend/tests/test_vm_service.py`:
  - **force_reset_vm**: any status (e.g., `"starting"`) → DB updated to `status='stopped'`, `error_message=None`, log inserted; no VBoxManage call made
  - **delete_vm on "error" state**: VBoxManage exit 0 → DB record deleted, log success (FR-010 extended path)
  - **create_vm quota exceeded**: mock count returns `VM_QUOTA_PER_USER` → `HTTPException` 409 `"VM quota reached"` raised before any VBoxManage call

- [X] T034 [P] Add `force_reset_vm` to `LogAction` enum in `backend/app/models/enums.py` if not already present; verify `ruff check .` passes after addition

---

## Dependency Graph

```
Phase 1 (Setup)
    ↓
Phase 2 (Foundational: T003 → T004 [P], T005)
    ↓
Phase 3 (US1: T006 → T007, T008 → T009 → T010)
    ↓
Phase 4 (US2: T011, T012, T013 → T014) — depends on get_vm_or_404 from T008
    ↓
Phase 5 (US3: T015 → T016)
    ↓
Phase 6 (US4: T017, T018 → T019 | T020 [P], T021 [P] → T022 → T023)
    ↓
Phase 7 (Tests: T024) — can overlap with Phase 6
    ↓
Phase 8 (Polish: T025–T029)
```

### Parallel Opportunities

- **Phase 2**: T003 (vbox_wrapper) → T005 (log helper) is sequential; T004 (schemas) is independent [P]
- **Phase 6**: T020 (vm-card) + T021 (vm-list) are independent [P]; T017 + T018 (admin backend) independent of frontend
- **Phase 7**: T024 can start once Phase 5 backend functions exist, overlapping with Phase 6 frontend work
- **Phase 9**: T034 (LogAction enum) is a prerequisite for T030; T031 depends on T030; T032 (frontend button) is independent [P] with T033 (tests) once T030 is done
