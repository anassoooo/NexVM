# Implementation Quality Checklist: VM P2 Lifecycle

**Purpose**: Validate implementation completeness before merging
**Created**: 2026-04-30

## DB Migration

- [ ] `vms_status_check` includes `paused`
- [ ] `nat_rules JSONB NOT NULL DEFAULT '[]'` added to `vms`
- [ ] `vm_snapshots` table created with `(vm_id, name)` unique constraint
- [ ] RLS enabled on `vm_snapshots` (user_own + admin_all policies)

## Backend — Enums, Schemas, Wrapper

- [ ] `VMStatus.paused` added
- [ ] 9 new `LogAction` values added
- [ ] `VBOXMANAGE_COMMANDS` includes `"snapshot"`
- [ ] `VBOX_STATE_MAP["paused"]` = `"paused"` (not `"stopped"`)
- [ ] `PortFwdRule` model defined
- [ ] `VMResponse.nat_rules: list[PortFwdRule]` added
- [ ] `VMModifyRequest` with `model_validator` requiring ≥1 field
- [ ] `PortFwdAddRequest`, `PortFwdDeleteRequest` defined
- [ ] `SnapshotTakeRequest`, `SnapshotActionRequest`, `SnapshotResponse` defined

## Backend — Services

- [ ] `modify_vm` enforces stopped state (409)
- [ ] `modify_vm` only sends non-None fields to VBoxManage
- [ ] `pause_vm` enforces running state (409)
- [ ] `pause_vm` updates status to `paused`
- [ ] `resume_vm` enforces paused state (409)
- [ ] `resume_vm` updates status to `running`
- [ ] `save_state` enforces running state (409)
- [ ] `save_state` sets transitional `stopping`, then `stopped` on success
- [ ] `add_port_rule` enforces stopped state + no duplicate name (409)
- [ ] `add_port_rule` appends to `nat_rules` JSONB
- [ ] `remove_port_rule` enforces stopped state (409) + rule exists (404)
- [ ] `remove_port_rule` removes from `nat_rules` JSONB
- [ ] `take_snapshot` enforces stopped state + no duplicate name (409)
- [ ] `take_snapshot` inserts into `vm_snapshots`
- [ ] `restore_snapshot` enforces stopped state (409) + snapshot exists (404)
- [ ] `delete_snapshot` enforces stopped state (409) + snapshot exists (404)
- [ ] `delete_snapshot` removes from `vm_snapshots`
- [ ] `list_snapshots` verifies VM ownership

## Backend — Routes

- [ ] 10 new endpoints registered in `routes/vm.py`
- [ ] All use `Depends(get_current_user)`
- [ ] `POST /snapshot` returns status 201
- [ ] `DELETE /snapshot` returns status 204

## Backend — Tests

- [ ] 16 test cases in `test_vm_p2_service.py`
- [ ] `pytest tests/test_vm_p2_service.py -v` — all pass
- [ ] `pytest -q` — all existing tests pass (no regressions)

## Frontend

- [ ] `VM.status` union includes `"paused"`
- [ ] `PortFwdRule` and `Snapshot` interfaces added
- [ ] `VM.nat_rules: PortFwdRule[]` added
- [ ] `STATUS_COLOR["paused"]` defined in `vm-card.tsx`
- [ ] Pause / Resume / Save State buttons wired with correct state guards
- [ ] Modify inline form (RAM + CPU) works on stopped VM
- [ ] Port-fwd section shows rules + add/remove
- [ ] Snapshot section shows list + take/restore/delete
- [ ] All new handlers in `vms-client.tsx` and `admin-vms-client.tsx`
- [ ] `vm-list.tsx` propagates all new props

## Type Safety & Lint

- [ ] `tsc --noEmit` — no errors
- [ ] `ruff check .` — zero errors

## Constitution Compliance

- [ ] §II: All new endpoints protected by JWT
- [ ] §V: Disk resize / live snapshots / hot port-fwd deferred (YAGNI)
- [ ] §XI.3: `snapshot` added to whitelist
- [ ] §XII.1: All 9 new operations logged
