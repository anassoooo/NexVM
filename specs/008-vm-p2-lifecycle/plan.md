# Implementation Plan: VM P2 Lifecycle

**Branch**: `004-analytics` | **Date**: 2026-04-30 | **Spec**: `specs/008-vm-p2-lifecycle/spec.md`

## Summary

Five lifecycle features: modify VM hardware, pause/resume, save state, port-forwarding
management, and snapshots. Requires a 3-part DB migration, backend service additions,
and frontend VM card extensions.

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript 5.x (frontend)
**Primary Dependencies**: FastAPI, Pydantic v2, supabase-py, VBoxManage, Next.js 14
**Storage**: Supabase — extend `vms` table + new `vm_snapshots` table
**Testing**: pytest — new service functions need test coverage
**Constraints**: `ruff check .` + `tsc --noEmit` must pass; 61 existing tests must pass

## Constitution Check

| Principle | Status | Notes |
|---|---|---|
| §II Auth Before Everything | ✅ PASS | All new endpoints use `get_current_user` |
| §V YAGNI | ✅ PASS | No disk resize, no live snapshots, no AI schemas — deferred |
| §VI.1 Separation of Concerns | ✅ PASS | Logic in `vm_service.py`, routes stay thin |
| §VI.2 API Versioning | ✅ PASS | All routes under `/api/v1/vm/` |
| §VI.3 No Direct Frontend DB Writes | ✅ PASS | Frontend calls FastAPI only |
| §VII Data Access Rules | ✅ PASS | All queries filter by `user_id` via `_get_vm_or_404` |
| §IX Backend Conventions | ✅ PASS | Python 3.12, Pydantic v2, ruff |
| §XI.2 Input Validation | ✅ PASS | Pydantic validates all new request schemas |
| §XI.3 Command Whitelist | ✅ PASS | `snapshot` added to VBOXMANAGE_COMMANDS |
| §XII.1 Mandatory Logging | ✅ PASS | 9 new LogAction values cover all state changes |

**Gate result**: ALL PASS — proceed to implementation.

## Project Structure

### Source Code (files touched)

```text
backend/
├── app/
│   ├── models/
│   │   ├── enums.py          # VMStatus.paused + 9 new LogActions
│   │   └── schemas.py        # PortFwdRule, VMModifyRequest, PortFwdAddRequest,
│   │                         # PortFwdDeleteRequest, SnapshotTakeRequest,
│   │                         # SnapshotActionRequest, SnapshotResponse
│   │                         # VMResponse.nat_rules
│   ├── services/
│   │   ├── vbox_wrapper.py   # VBOXMANAGE_COMMANDS += snapshot; VBOX_STATE_MAP paused fix
│   │   └── vm_service.py     # 8 new functions
│   └── routes/
│       └── vm.py             # 8 new endpoints + GET /snapshots
├── tests/
│   └── test_vm_p2_service.py # 16 test cases
frontend/
├── types/
│   └── index.ts              # VM.status + paused, nat_rules, Snapshot, PortFwdRule
├── components/
│   ├── vm-card.tsx           # pause/resume/save-state buttons, modify form,
│   │                         # port-fwd section, snapshot section
│   ├── vms-client.tsx        # new handlers
│   ├── admin-vms-client.tsx  # new handlers
│   └── vm-list.tsx           # new props
```

---

## Tasks

### T001 — DB migration (3 steps)

1. Extend `vms_status_check` to include `paused`
2. Add `nat_rules jsonb NOT NULL DEFAULT '[]'` to `vms`
3. Create `vm_snapshots` table with RLS

Write to `specs/008-vm-p2-lifecycle/migration.sql`.

### T002 — Backend: enums + schemas + vbox_wrapper

**`enums.py`**:
- `VMStatus`: add `paused`
- `LogAction`: add 9 new values (`modify_vm`, `pause_vm`, `resume_vm`, `save_state`,
  `add_port_rule`, `remove_port_rule`, `take_snapshot`, `restore_snapshot`, `delete_snapshot`)

**`vbox_wrapper.py`**:
- `VBOXMANAGE_COMMANDS`: add `"snapshot"`
- `VBOX_STATE_MAP`: change `"paused": "stopped"` → `"paused": "paused"`

**`schemas.py`**:
- Add `PortFwdRule` model
- `VMResponse`: add `nat_rules: list[PortFwdRule]`
- Add `VMModifyRequest` with `model_validator` requiring ≥1 field
- Add `PortFwdAddRequest`, `PortFwdDeleteRequest`
- Add `SnapshotTakeRequest`, `SnapshotActionRequest`, `SnapshotResponse`

### T003 — vm_service: modify_vm

`modify_vm(vm_id, ram, cpu, user_id)`:
1. `_get_vm_or_404` → assert stopped else 409
2. Build `modifyvm` args from non-None fields
3. `_run_vbox([vbox, "modifyvm", vm_name, "--memory", str(ram), "--cpus", str(cpu)])`
4. Update DB, log `modify_vm`, return `VMResponse`

### T004 — vm_service: pause_vm + resume_vm

`pause_vm(vm_id, user_id)`:
1. `_get_vm_or_404` → assert `status == "running"` else 409
2. `run_vbox_command([vbox, "controlvm", vm_name, "pause"])`
3. Update DB `status = "paused"`, log `pause_vm`

`resume_vm(vm_id, user_id)`:
1. `_get_vm_or_404` → assert `status == "paused"` else 409
2. `run_vbox_command([vbox, "controlvm", vm_name, "resume"])`
3. Update DB `status = "running"`, log `resume_vm`

### T005 — vm_service: save_state

`save_state(vm_id, user_id)`:
1. `_get_vm_or_404` → assert `status == "running"` else 409
2. Update DB `status = "stopping"` (transitional)
3. `run_vbox_command([vbox, "controlvm", vm_name, "savestate"])`
4. On success: update DB `status = "stopped"`, log `save_state`
5. On failure: update DB `status = "error"`, raise 500

### T006 — vm_service: add_port_rule + remove_port_rule

`add_port_rule(vm_id, name, protocol, host_port, guest_port, user_id)`:
1. `_get_vm_or_404` → assert stopped else 409
2. Check rule name uniqueness in `vm["nat_rules"]` → 409 if duplicate
3. `_run_vbox([vbox, "modifyvm", vm_name, "--natpf1", f"{name},{protocol},,{host_port},,{guest_port}"])`
4. Append rule to `nat_rules` JSONB, update DB, log `add_port_rule`

`remove_port_rule(vm_id, name, user_id)`:
1. `_get_vm_or_404` → assert stopped else 409
2. Find rule in `vm["nat_rules"]` → 404 if not found
3. `_run_vbox([vbox, "modifyvm", vm_name, "--natpf1", f"delete {name}"])`
4. Remove rule from `nat_rules` JSONB, update DB, log `remove_port_rule`

### T007 — vm_service: snapshot functions

`take_snapshot(vm_id, name, description, user_id)`:
1. `_get_vm_or_404` → assert stopped else 409
2. Check name uniqueness in `vm_snapshots` → 409 if duplicate
3. `_run_vbox([vbox, "snapshot", vm_name, "take", name, "--description", description])`
4. Insert row into `vm_snapshots`, log `take_snapshot`, return `SnapshotResponse`

`restore_snapshot(vm_id, name, user_id)`:
1. `_get_vm_or_404` → assert stopped else 409
2. Verify snapshot exists in `vm_snapshots` → 404 if not
3. `_run_vbox([vbox, "snapshot", vm_name, "restore", name])`
4. Log `restore_snapshot`, return `VMResponse`

`delete_snapshot(vm_id, name, user_id)`:
1. `_get_vm_or_404` → assert stopped else 409
2. Verify snapshot exists → 404 if not
3. `_run_vbox([vbox, "snapshot", vm_name, "delete", name])`
4. Delete row from `vm_snapshots`, log `delete_snapshot`

`list_snapshots(vm_id, user_id)`:
1. `_get_vm_or_404` → verifies ownership
2. Query `vm_snapshots` where `vm_id = vm_id`
3. Return `list[SnapshotResponse]`

### T008 — Backend: routes (9 new endpoints)

```
POST   /api/v1/vm/modify          → modify_vm
POST   /api/v1/vm/pause           → pause_vm
POST   /api/v1/vm/resume          → resume_vm
POST   /api/v1/vm/savestate       → save_state
POST   /api/v1/vm/portfwd         → add_port_rule
DELETE /api/v1/vm/portfwd         → remove_port_rule
POST   /api/v1/vm/snapshot        → take_snapshot
DELETE /api/v1/vm/snapshot        → delete_snapshot
POST   /api/v1/vm/snapshot/restore → restore_snapshot
GET    /api/v1/vm/snapshots        → list_snapshots (query param: vm_id)
```

### T009 — Backend: tests (16 cases)

**`tests/test_vm_p2_service.py`**:
- `test_modify_vm_ok`
- `test_modify_vm_not_stopped` → 409
- `test_modify_vm_no_fields` → 422
- `test_pause_vm_ok`
- `test_pause_vm_not_running` → 409
- `test_resume_vm_ok`
- `test_resume_vm_not_paused` → 409
- `test_save_state_ok`
- `test_save_state_not_running` → 409
- `test_add_port_rule_ok`
- `test_add_port_rule_duplicate` → 409
- `test_remove_port_rule_ok`
- `test_remove_port_rule_not_found` → 404
- `test_take_snapshot_ok`
- `test_restore_snapshot_ok`
- `test_delete_snapshot_ok`

### T010 — Frontend: types + vm-card

**`types/index.ts`**:
- `VM.status`: add `"paused"`
- Add `nat_rules: PortFwdRule[]`
- Add `PortFwdRule` and `Snapshot` interfaces

**`vm-card.tsx`** additions:
- `STATUS_COLOR["paused"]` → `"var(--accent)"` (cyan)
- Pause button: visible + enabled when `status === "running"`
- Resume button: visible + enabled when `status === "paused"`
- Save State button: visible + enabled when `status === "running"`
- Modify section: inline form for RAM/CPU (visible when stopped, opens on click)
- Port-fwd section: expandable list of `vm.nat_rules` + add/remove form
- Snapshots section: expandable (requires fetching list separately)

### T011 — Frontend: clients

**`vms-client.tsx`** and **`admin-vms-client.tsx`**:
- Add handlers: `handlePause`, `handleResume`, `handleSaveState`, `handleModify`,
  `handleAddPortRule`, `handleRemovePortRule`, `handleTakeSnapshot`,
  `handleRestoreSnapshot`, `handleDeleteSnapshot`
- Wire up to `VMList` → `VMCard`

**`vm-list.tsx`**: add new props for all new handlers

### T012 — Verify: ruff + tsc + pytest

```bash
cd backend && ruff check . && pytest
cd ../frontend && npx tsc --noEmit
```
