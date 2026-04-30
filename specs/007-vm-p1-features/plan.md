# Implementation Plan: VM P1 Features

**Branch**: `004-analytics` | **Date**: 2026-04-30 | **Spec**: `specs/007-vm-p1-features/spec.md`

## Summary

Three features to make the VM module usable: ISO attachment, VRDE remote access,
and frontend auto-polling for transitional states. Requires a DB migration, backend
service/route additions, and frontend component updates.

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript 5.x (frontend)
**Primary Dependencies**: FastAPI, Pydantic v2, supabase-py, VBoxManage, Next.js 14
**Storage**: Supabase — three new columns on `vms`, no new tables
**Testing**: pytest — new service functions need test coverage
**Target Platform**: Windows 11 host with VirtualBox
**Constraints**: `ruff check .` and `tsc --noEmit` must pass; no regressions

## Constitution Check

| Principle | Status | Notes |
|---|---|---|
| §II Auth Before Everything | ✅ PASS | All new endpoints use `get_current_user` |
| §V YAGNI | ✅ PASS | No hot-attach, no auto-port, no AI schemas — scope is exact |
| §VI.1 Separation of Concerns | ✅ PASS | Business logic in `vm_service.py`, routes stay thin |
| §VI.2 API Versioning | ✅ PASS | New routes under `/api/v1/vm/` |
| §VI.3 No Direct Frontend DB Writes | ✅ PASS | Frontend calls FastAPI only |
| §VII Data Access Rules | ✅ PASS | All queries filter by `user_id` |
| §IX Backend Conventions | ✅ PASS | Python 3.12, Pydantic v2, ruff |
| §XI.2 Input Validation | ✅ PASS | Pydantic validators on `iso_path` and `port` |
| §XI.3 Command Whitelist | ✅ PASS | `storageattach`, `storagectl`, `modifyvm` already whitelisted |
| §XII.1 Mandatory Logging | ✅ PASS | 4 new `LogAction` values for all state changes |

**Gate result**: ALL PASS — proceed to implementation.

## Project Structure

### Documentation (this feature)

```text
specs/007-vm-p1-features/
├── spec.md
├── plan.md              ← this file
├── research.md
├── data-model.md
├── quickstart.md
├── tasks.md
├── contracts/
│   └── vm-api.md
└── checklists/
    ├── requirements.md
    └── implementation.md
```

### Source Code (files touched)

```text
backend/
├── app/
│   ├── models/
│   │   ├── enums.py          # add attach_iso, detach_iso, enable_vrde, disable_vrde
│   │   └── schemas.py        # VMResponse + 4 new request schemas
│   ├── services/
│   │   └── vm_service.py     # attach_iso, detach_iso, enable_vrde, disable_vrde
│   └── routes/
│       └── vm.py             # 4 new endpoints
├── tests/
│   └── test_vm_p1_service.py # new test file
frontend/
├── types/
│   └── index.ts              # VM interface: iso_path, vrde_enabled, vrde_port
├── components/
│   ├── vm-card.tsx           # ISO badge, VRDE badge + toggle
│   ├── vms-client.tsx        # auto-polling useEffect
│   └── admin-vms-client.tsx  # auto-polling useEffect
```

### DB migration (applied manually via Supabase SQL editor)

```text
specs/007-vm-p1-features/migration.sql   ← created in T001
```

---

## Tasks

### T001 — DB migration: add iso_path, vrde_enabled, vrde_port to vms

Apply via Supabase SQL editor:
```sql
ALTER TABLE public.vms
  ADD COLUMN IF NOT EXISTS iso_path     text,
  ADD COLUMN IF NOT EXISTS vrde_enabled boolean NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS vrde_port    integer;

ALTER TABLE public.vms
  ADD CONSTRAINT vms_vrde_port_check
    CHECK (vrde_port IS NULL OR (vrde_port >= 1024 AND vrde_port <= 65535));
```
Also write to `specs/007-vm-p1-features/migration.sql`.

### T002 — Backend: enums + schemas

**`enums.py`**: add `attach_iso`, `detach_iso`, `enable_vrde`, `disable_vrde` to `LogAction`.

**`schemas.py`**:
- `VMResponse`: add `iso_path: str | None`, `vrde_enabled: bool`, `vrde_port: int | None`
- Add `ISOAttachRequest`, `ISODetachRequest`, `VRDEEnableRequest`, `VRDEDisableRequest`
- `ISOAttachRequest.iso_path` validator: must be absolute path, must end with `.iso`

### T003 — Backend: vm_service — attach_iso + detach_iso

**`vm_service.py`**: add two functions.

`attach_iso(vm_id, iso_path, user_id)`:
1. `_get_vm_or_404(vm_id, user_id)` — assert status == "stopped" (else 409)
2. Verify `os.path.exists(iso_path)` — else 422
3. Run `storagectl <name> --name "IDE" --add ide` — swallow "already exists" error
4. Run `storageattach <name> --storagectl IDE --port 0 --device 0 --type dvddrive --medium <iso_path>`
5. Update DB: `iso_path = iso_path`
6. Log `LogAction.attach_iso`
7. Return updated `VMResponse`

`detach_iso(vm_id, user_id)`:
1. `_get_vm_or_404(vm_id, user_id)` — assert status == "stopped" + iso_path not null (else 409)
2. Run `storageattach <name> --storagectl IDE --port 0 --device 0 --type dvddrive --medium emptydrive`
3. Update DB: `iso_path = None`
4. Log `LogAction.detach_iso`
5. Return updated `VMResponse`

### T004 — Backend: vm_service — enable_vrde + disable_vrde

**`vm_service.py`**: add two functions.

`enable_vrde(vm_id, port, user_id)`:
1. `_get_vm_or_404(vm_id, user_id)` — assert status == "stopped" (else 409)
2. Check port uniqueness: query `vms` where `vrde_port == port AND id != vm_id` — if found, 409
3. Run `modifyvm <name> --vrde on --vrdeport <port>`
4. Update DB: `vrde_enabled = True`, `vrde_port = port`
5. Log `LogAction.enable_vrde`
6. Return updated `VMResponse`

`disable_vrde(vm_id, user_id)`:
1. `_get_vm_or_404(vm_id, user_id)` — assert status == "stopped" + vrde_enabled == True (else 409)
2. Run `modifyvm <name> --vrde off`
3. Update DB: `vrde_enabled = False`, `vrde_port = None`
4. Log `LogAction.disable_vrde`
5. Return updated `VMResponse`

### T005 — Backend: routes — 4 new endpoints

**`routes/vm.py`**: add four endpoints.

```
POST   /api/v1/vm/iso          → attach_iso
DELETE /api/v1/vm/iso          → detach_iso
POST   /api/v1/vm/vrde         → enable_vrde
DELETE /api/v1/vm/vrde         → disable_vrde
```

All use `Depends(get_current_user)`. Routes are thin — delegate to service.

### T006 — Backend: tests

**`tests/test_vm_p1_service.py`**: cover:
- `attach_iso` happy path
- `attach_iso` — VM not stopped → 409
- `attach_iso` — ISO path not found → 422
- `detach_iso` happy path
- `detach_iso` — no ISO attached → 409
- `enable_vrde` happy path
- `enable_vrde` — VM not stopped → 409
- `enable_vrde` — port conflict → 409
- `disable_vrde` happy path
- `disable_vrde` — VRDE already off → 409

### T007 — Frontend: types + vm-card

**`types/index.ts`**: add `iso_path: string | null`, `vrde_enabled: boolean`, `vrde_port: number | null` to `VM`.

**`vm-card.tsx`**:
- ISO row: if `vm.iso_path`, show filename (basename) in muted text with a disc icon placeholder
- VRDE row: if `vm.vrde_enabled`, show `RDP :<port>` in accent color
- Add "Attach ISO" button (shows inline path input, calls `POST /api/v1/vm/iso`)
- Add "Detach ISO" button (visible when iso_path not null, VM stopped)
- Add "Enable VRDE" button (shows inline port input, calls `POST /api/v1/vm/vrde`)
- Add "Disable VRDE" button (visible when vrde_enabled, VM stopped)
- All ISO/VRDE buttons disabled when `loading` or VM not in `stopped` state

### T008 — Frontend: auto-polling in vms-client + admin-vms-client

**`vms-client.tsx`** and **`admin-vms-client.tsx`**: add `useEffect`:

```ts
useEffect(() => {
  const hasTransitional = vms.some(
    (v) => v.status === "starting" || v.status === "stopping"
  );
  if (!hasTransitional) return;
  const id = setInterval(() => void refetch(), 5000);
  return () => clearInterval(id);
}, [vms]);
```

### T009 — Verify: ruff + tsc + pytest

```bash
cd backend && ruff check . && pytest
cd frontend && npx tsc --noEmit
```
