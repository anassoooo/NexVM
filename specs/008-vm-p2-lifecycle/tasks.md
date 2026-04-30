# Tasks — Spec 008 VM P2 Lifecycle

**Branch**: `004-analytics`
**Total tasks**: 12

| ID | Title | Status |
|---|---|---|
| T001 | DB migration — paused status + nat_rules + vm_snapshots | pending |
| T002 | Backend: enums + schemas + vbox_wrapper | pending |
| T003 | vm_service: modify_vm | pending |
| T004 | vm_service: pause_vm + resume_vm | pending |
| T005 | vm_service: save_state | pending |
| T006 | vm_service: add_port_rule + remove_port_rule | pending |
| T007 | vm_service: take_snapshot + restore_snapshot + delete_snapshot + list_snapshots | pending |
| T008 | Backend routes — 10 new endpoints | pending |
| T009 | Backend tests — 16 cases | pending |
| T010 | Frontend: types + vm-card | pending |
| T011 | Frontend: vms-client + admin-vms-client + vm-list | pending |
| T012 | Verify: ruff + tsc + pytest | pending |

---

## T001 — DB migration

Apply `specs/008-vm-p2-lifecycle/migration.sql` via Supabase SQL Editor.

**Done when**: `vms` has `nat_rules` column; `paused` is a valid status; `vm_snapshots` table exists.

---

## T002 — Backend: enums + schemas + vbox_wrapper

### `enums.py`
- `VMStatus`: add `paused = "paused"`
- `LogAction`: add `modify_vm`, `pause_vm`, `resume_vm`, `save_state`, `add_port_rule`, `remove_port_rule`, `take_snapshot`, `restore_snapshot`, `delete_snapshot`

### `vbox_wrapper.py`
- `VBOXMANAGE_COMMANDS`: add `"snapshot"`
- `VBOX_STATE_MAP`: `"paused": "paused"` (was `"stopped"`)

### `schemas.py`
- Add `PortFwdRule(name, protocol, host_port, guest_port)` — not a request schema, used in response
- `VMResponse`: add `nat_rules: list[PortFwdRule]`
- Add `VMModifyRequest(vm_id, ram?, cpu?)` with `model_validator` requiring ≥1 field
- Add `PortFwdAddRequest(vm_id, name, protocol, host_port, guest_port)`
- Add `PortFwdDeleteRequest(vm_id, name)`
- Add `SnapshotTakeRequest(vm_id, name, description="")`
- Add `SnapshotActionRequest(vm_id, name)` — used for restore + delete
- Add `SnapshotResponse(id, vm_id, name, description, created_at)`

**Done when**: `ruff check .` passes.

---

## T003 — vm_service: modify_vm

```python
def modify_vm(vm_id: str, ram: int | None, cpu: int | None, user_id: str) -> VMResponse
```

- Assert `status == "stopped"` else 409
- Build modifyvm args: only include `--memory` / `--cpus` for non-None values
- `_run_vbox([vbox, "modifyvm", vm_name, *args], user_id, LogAction.modify_vm, "modifyvm modify")`
- Update DB with new values, log, return VMResponse

---

## T004 — vm_service: pause_vm + resume_vm

```python
def pause_vm(vm_id: str, user_id: str) -> VMResponse
def resume_vm(vm_id: str, user_id: str) -> VMResponse
```

`pause_vm`:
- Assert `status == "running"` else 409
- `run_vbox_command([vbox, "controlvm", vm_name, "pause"])`
- Update DB `status = "paused"`, log `pause_vm`

`resume_vm`:
- Assert `status == "paused"` else 409
- `run_vbox_command([vbox, "controlvm", vm_name, "resume"])`
- Update DB `status = "running"`, log `resume_vm`

---

## T005 — vm_service: save_state

```python
def save_state(vm_id: str, user_id: str) -> VMResponse
```

- Assert `status == "running"` else 409
- Update DB `status = "stopping"`
- `run_vbox_command([vbox, "controlvm", vm_name, "savestate"])`
- On success: Update DB `status = "stopped"`, log `save_state`
- On failure: Update DB `status = "error"`, raise 500

---

## T006 — vm_service: add_port_rule + remove_port_rule

```python
def add_port_rule(vm_id, name, protocol, host_port, guest_port, user_id) -> VMResponse
def remove_port_rule(vm_id, name, user_id) -> VMResponse
```

`add_port_rule`:
- Assert stopped else 409
- Check rule name not in `vm["nat_rules"]` list → 409 if duplicate
- `_run_vbox([vbox, "modifyvm", vm_name, "--natpf1", f"{name},{protocol},,{host_port},,{guest_port}"])`
- `nat_rules = vm["nat_rules"] + [{"name": name, "protocol": protocol, "host_port": host_port, "guest_port": guest_port}]`
- Update DB `nat_rules = json.dumps(nat_rules)`, log

`remove_port_rule`:
- Assert stopped else 409
- Find rule by name → 404 if not found
- `_run_vbox([vbox, "modifyvm", vm_name, "--natpf1", f"delete {name}"])`
- Filter rule out of list, update DB, log

---

## T007 — vm_service: snapshot functions

```python
def take_snapshot(vm_id, name, description, user_id) -> SnapshotResponse
def restore_snapshot(vm_id, name, user_id) -> VMResponse
def delete_snapshot(vm_id, name, user_id) -> None
def list_snapshots(vm_id, user_id) -> list[SnapshotResponse]
```

`take_snapshot`:
- Assert stopped else 409
- Check name uniqueness in `vm_snapshots` → 409 if duplicate
- `_run_vbox([vbox, "snapshot", vm_name, "take", name, "--description", description])`
- Insert into `vm_snapshots`, return `SnapshotResponse`

`restore_snapshot`:
- Assert stopped else 409
- Verify snapshot in `vm_snapshots` → 404 if not found
- `_run_vbox([vbox, "snapshot", vm_name, "restore", name])`
- Log, return `VMResponse`

`delete_snapshot`:
- Assert stopped else 409
- Verify snapshot → 404 if not found
- `_run_vbox([vbox, "snapshot", vm_name, "delete", name])`
- Delete from `vm_snapshots`, log

`list_snapshots`:
- `_get_vm_or_404` → verifies ownership
- Query `vm_snapshots` where `vm_id = vm_id` ordered by `created_at desc`
- Return list

---

## T008 — Backend routes

Add to `routes/vm.py`:

```
POST   /modify           VMModifyRequest         → modify_vm
POST   /pause            VMActionRequest         → pause_vm
POST   /resume           VMActionRequest         → resume_vm
POST   /savestate        VMActionRequest         → save_state
POST   /portfwd          PortFwdAddRequest       → add_port_rule
DELETE /portfwd          PortFwdDeleteRequest    → remove_port_rule
GET    /snapshots         ?vm_id=<uuid>          → list_snapshots
POST   /snapshot         SnapshotTakeRequest     → take_snapshot  → 201
POST   /snapshot/restore SnapshotActionRequest   → restore_snapshot
DELETE /snapshot         SnapshotActionRequest   → delete_snapshot → 204
```

---

## T009 — Backend tests

**`tests/test_vm_p2_service.py`** — 16 cases:

1. `test_modify_vm_ok` — ram + cpu updated
2. `test_modify_vm_not_stopped` — 409
3. `test_modify_vm_no_fields` — VMModifyRequest raises ValueError (422 at route)
4. `test_pause_vm_ok` — status → paused
5. `test_pause_vm_not_running` — 409
6. `test_resume_vm_ok` — status → running
7. `test_resume_vm_not_paused` — 409
8. `test_save_state_ok` — status → stopped
9. `test_save_state_not_running` — 409
10. `test_add_port_rule_ok` — rule in nat_rules
11. `test_add_port_rule_duplicate` — 409
12. `test_remove_port_rule_ok` — rule removed
13. `test_remove_port_rule_not_found` — 404
14. `test_take_snapshot_ok` — snapshot row created
15. `test_restore_snapshot_ok` — VBoxManage called
16. `test_delete_snapshot_ok` — snapshot row deleted

---

## T010 — Frontend: types + vm-card

**`types/index.ts`**:
- `VM.status`: add `"paused"`
- Add `nat_rules: PortFwdRule[]`
- Add `PortFwdRule` interface
- Add `Snapshot` interface

**`vm-card.tsx`**:
- Add `paused` to `STATUS_COLOR` (use `"var(--accent)"`)
- New props: `onPause`, `onResume`, `onSaveState`, `onModify(ram,cpu)`, `onAddPortRule(name,proto,hp,gp)`, `onRemovePortRule(name)`, `onTakeSnapshot(name,desc)`, `onRestoreSnapshot(name)`, `onDeleteSnapshot(name)`
- Button row: add Pause (running only), Resume (paused only), Save State (running only)
- Modify section: inline form RAM+CPU fields (stopped only, opens on click)
- Port-fwd section: expandable, shows `vm.nat_rules`, add form, delete per rule
- Snapshot section: loads snapshots separately (fetch on expand), take form, restore/delete per snapshot
- All new buttons disabled when `loading` or state constraint not met

---

## T011 — Frontend: clients + vm-list

**`vm-list.tsx`**: add all new handler props

**`vms-client.tsx`** and **`admin-vms-client.tsx`**:
- Add `handlePause`, `handleResume`, `handleSaveState`
- Add `handleModify(id, ram, cpu)`
- Add `handleAddPortRule(id, name, proto, hp, gp)`, `handleRemovePortRule(id, name)`
- Add `handleTakeSnapshot(id, name, desc)`, `handleRestoreSnapshot(id, name)`, `handleDeleteSnapshot(id, name)`

---

## T012 — Verify

```bash
cd backend && ruff check . && pytest
cd ../frontend && npx tsc --noEmit
```
