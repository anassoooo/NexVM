# Implementation Quality Checklist: VM P1 Features

**Purpose**: Validate implementation completeness before merging
**Created**: 2026-04-30
**Feature**: [spec.md](../spec.md)

## DB Migration

- [ ] `iso_path TEXT` column added to `vms`
- [ ] `vrde_enabled BOOLEAN NOT NULL DEFAULT false` column added to `vms`
- [ ] `vrde_port INTEGER` column added to `vms`
- [ ] `vms_vrde_port_check` constraint added
- [ ] Existing rows unaffected (iso_path=null, vrde_enabled=false, vrde_port=null)

## Backend — Enums & Schemas

- [ ] `LogAction` has `attach_iso`, `detach_iso`, `enable_vrde`, `disable_vrde`
- [ ] `VMResponse` has `iso_path`, `vrde_enabled`, `vrde_port`
- [ ] `ISOAttachRequest` defined with `iso_path` validator (absolute path + .iso extension)
- [ ] `ISODetachRequest` defined
- [ ] `VRDEEnableRequest` defined with `port: int = Field(ge=1024, le=65535)`
- [ ] `VRDEDisableRequest` defined

## Backend — Services

- [ ] `attach_iso` enforces stopped state (409 otherwise)
- [ ] `attach_iso` validates iso_path exists on host (422 otherwise)
- [ ] `attach_iso` runs `storagectl --add ide` (swallows "already exists")
- [ ] `attach_iso` runs `storageattach --medium <path>`
- [ ] `attach_iso` updates DB and logs `attach_iso` action
- [ ] `detach_iso` enforces stopped state + iso_path not null (409 otherwise)
- [ ] `detach_iso` runs `storageattach --medium emptydrive`
- [ ] `detach_iso` updates DB iso_path to null and logs `detach_iso`
- [ ] `enable_vrde` enforces stopped state (409 otherwise)
- [ ] `enable_vrde` checks port uniqueness across all VMs (409 on conflict)
- [ ] `enable_vrde` runs `modifyvm --vrde on --vrdeport <port>`
- [ ] `enable_vrde` updates DB and logs `enable_vrde`
- [ ] `disable_vrde` enforces stopped state + vrde_enabled == True (409 otherwise)
- [ ] `disable_vrde` runs `modifyvm --vrde off`
- [ ] `disable_vrde` updates DB and logs `disable_vrde`

## Backend — Routes

- [ ] `POST /api/v1/vm/iso` registered and delegates to `attach_iso`
- [ ] `DELETE /api/v1/vm/iso` registered and delegates to `detach_iso`
- [ ] `POST /api/v1/vm/vrde` registered and delegates to `enable_vrde`
- [ ] `DELETE /api/v1/vm/vrde` registered and delegates to `disable_vrde`
- [ ] All endpoints use `Depends(get_current_user)`

## Backend — Tests

- [ ] 10 test cases in `test_vm_p1_service.py`
- [ ] All happy paths covered
- [ ] All 409/422 error paths covered
- [ ] `pytest tests/test_vm_p1_service.py -v` — all pass
- [ ] `pytest -q` — no regressions

## Frontend

- [ ] `VM` interface has `iso_path`, `vrde_enabled`, `vrde_port`
- [ ] `vm-card.tsx` shows ISO filename when `iso_path` is set
- [ ] `vm-card.tsx` shows `RDP :<port>` when `vrde_enabled`
- [ ] Attach/detach ISO buttons wired up and disabled when VM not stopped
- [ ] Enable/disable VRDE buttons wired up and disabled when VM not stopped
- [ ] Auto-polling `useEffect` added to `vms-client.tsx`
- [ ] Auto-polling `useEffect` added to `admin-vms-client.tsx`
- [ ] Polling fires every 5s when any VM is in `starting`/`stopping`
- [ ] Polling stops when all VMs are stable
- [ ] `clearInterval` called on cleanup (no memory leaks)

## Type Safety & Lint

- [ ] `tsc --noEmit` — no TypeScript errors
- [ ] `ruff check .` — zero errors

## Constitution Compliance

- [ ] §II: All new endpoints protected by JWT
- [ ] §V: No AI schemas, no auto-port, no hot-attach (YAGNI deferred)
- [ ] §VI.3: No direct frontend DB writes
- [ ] §XI.2: Pydantic validates iso_path and port before processing
- [ ] §XI.3: `storageattach`, `storagectl`, `modifyvm` all whitelisted
- [ ] §XII.1: All 4 new operations logged to `logs` table
