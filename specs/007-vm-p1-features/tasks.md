# Tasks — Spec 007 VM P1 Features

**Branch**: `004-analytics`
**Total tasks**: 9

| ID | Title | Status |
|---|---|---|
| T001 | DB migration — add iso_path, vrde_enabled, vrde_port | pending |
| T002 | Backend: enums + schemas | pending |
| T003 | Backend: vm_service — attach_iso + detach_iso | pending |
| T004 | Backend: vm_service — enable_vrde + disable_vrde | pending |
| T005 | Backend: routes — 4 new endpoints | pending |
| T006 | Backend: tests | pending |
| T007 | Frontend: types + vm-card | pending |
| T008 | Frontend: auto-polling (vms-client + admin-vms-client) | pending |
| T009 | Verify: ruff + tsc + pytest | pending |

---

## T001 — DB migration

Apply via Supabase SQL editor. Also write `specs/007-vm-p1-features/migration.sql`.

```sql
ALTER TABLE public.vms
  ADD COLUMN IF NOT EXISTS iso_path     text,
  ADD COLUMN IF NOT EXISTS vrde_enabled boolean NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS vrde_port    integer;

ALTER TABLE public.vms
  ADD CONSTRAINT vms_vrde_port_check
    CHECK (vrde_port IS NULL OR (vrde_port >= 1024 AND vrde_port <= 65535));
```

**Done when**: Supabase table has 3 new columns; existing rows have `vrde_enabled=false`, others null.

---

## T002 — Backend: enums + schemas

**`backend/app/models/enums.py`**
- Add to `LogAction`: `attach_iso`, `detach_iso`, `enable_vrde`, `disable_vrde`

**`backend/app/models/schemas.py`**
- `VMResponse`: add `iso_path: str | None`, `vrde_enabled: bool`, `vrde_port: int | None`
- Add `ISOAttachRequest(vm_id, iso_path)` with `iso_path` validator
- Add `ISODetachRequest(vm_id)`
- Add `VRDEEnableRequest(vm_id, port: int = Field(ge=1024, le=65535))`
- Add `VRDEDisableRequest(vm_id)`

**Done when**: `ruff check .` passes; no import errors.

---

## T003 — Backend: vm_service — attach_iso + detach_iso

**`backend/app/services/vm_service.py`**

`attach_iso(vm_id: str, iso_path: str, user_id: str) -> VMResponse`:
1. `vm = _get_vm_or_404(vm_id, user_id)` → assert `vm["status"] == "stopped"` else 409
2. `os.path.exists(iso_path)` → else 422
3. `run_vbox_command([vbox, "storagectl", vm_name, "--name", "IDE", "--add", "ide", "--controller", "PIIX4"])` — swallow "already exists" returncode != 0 only if stderr contains "already"
4. `run_vbox_command([vbox, "storageattach", vm_name, "--storagectl", "IDE", "--port", "0", "--device", "0", "--type", "dvddrive", "--medium", iso_path])`
5. Update DB `iso_path = iso_path`, return `VMResponse`
6. `_log_action(user_id, LogAction.attach_iso, vm_name, LogStatus.success, iso_path)`

`detach_iso(vm_id: str, user_id: str) -> VMResponse`:
1. `vm = _get_vm_or_404(vm_id, user_id)` → assert stopped + `vm["iso_path"]` not null else 409
2. `run_vbox_command([vbox, "storageattach", vm_name, "--storagectl", "IDE", "--port", "0", "--device", "0", "--type", "dvddrive", "--medium", "emptydrive"])`
3. Update DB `iso_path = None`, return `VMResponse`
4. `_log_action(user_id, LogAction.detach_iso, vm_name, LogStatus.success, "detached")`

**Done when**: functions exist; ruff passes.

---

## T004 — Backend: vm_service — enable_vrde + disable_vrde

**`backend/app/services/vm_service.py`**

`enable_vrde(vm_id: str, port: int, user_id: str) -> VMResponse`:
1. `vm = _get_vm_or_404(vm_id, user_id)` → assert stopped else 409
2. Check port uniqueness: query `vms` where `vrde_port == port AND id != vm_id` — if found 409
3. `run_vbox_command([vbox, "modifyvm", vm_name, "--vrde", "on", "--vrdeport", str(port)])`
4. Update DB `vrde_enabled = True`, `vrde_port = port`, return `VMResponse`
5. `_log_action(user_id, LogAction.enable_vrde, vm_name, LogStatus.success, str(port))`

`disable_vrde(vm_id: str, user_id: str) -> VMResponse`:
1. `vm = _get_vm_or_404(vm_id, user_id)` → assert stopped + vrde_enabled == True else 409
2. `run_vbox_command([vbox, "modifyvm", vm_name, "--vrde", "off"])`
3. Update DB `vrde_enabled = False`, `vrde_port = None`, return `VMResponse`
4. `_log_action(user_id, LogAction.disable_vrde, vm_name, LogStatus.success, "disabled")`

**Done when**: functions exist; ruff passes.

---

## T005 — Backend: routes — 4 new endpoints

**`backend/app/routes/vm.py`**

```python
from app.models.schemas import ISOAttachRequest, ISODetachRequest, VRDEEnableRequest, VRDEDisableRequest

@router.post("/iso", response_model=VMResponse)
async def attach_iso(body: ISOAttachRequest, current_user_id: str = Depends(get_current_user)):
    return vm_service.attach_iso(str(body.vm_id), body.iso_path, current_user_id)

@router.delete("/iso", response_model=VMResponse)
async def detach_iso(body: ISODetachRequest, current_user_id: str = Depends(get_current_user)):
    return vm_service.detach_iso(str(body.vm_id), current_user_id)

@router.post("/vrde", response_model=VMResponse)
async def enable_vrde(body: VRDEEnableRequest, current_user_id: str = Depends(get_current_user)):
    return vm_service.enable_vrde(str(body.vm_id), body.port, current_user_id)

@router.delete("/vrde", response_model=VMResponse)
async def disable_vrde(body: VRDEDisableRequest, current_user_id: str = Depends(get_current_user)):
    return vm_service.disable_vrde(str(body.vm_id), current_user_id)
```

**Done when**: routes registered; `GET /api/v1/vm/iso` returns 405 (wrong method, not 404).

---

## T006 — Backend: tests

**`backend/tests/test_vm_p1_service.py`** — 10 test cases with mocked Supabase + VBoxManage:

1. `test_attach_iso_ok` — happy path, DB updated, log inserted
2. `test_attach_iso_vm_not_stopped` — 409 when status != stopped
3. `test_attach_iso_path_not_found` — 422 when file doesn't exist
4. `test_detach_iso_ok` — happy path, iso_path set to None
5. `test_detach_iso_no_iso` — 409 when iso_path already null
6. `test_enable_vrde_ok` — happy path, vrde_enabled=True, vrde_port set
7. `test_enable_vrde_vm_not_stopped` — 409
8. `test_enable_vrde_port_conflict` — 409 when port already used
9. `test_disable_vrde_ok` — happy path
10. `test_disable_vrde_already_off` — 409 when vrde_enabled=False

**Done when**: `pytest tests/test_vm_p1_service.py -v` all pass; `pytest -q` no regressions.

---

## T007 — Frontend: types + vm-card

**`frontend/types/index.ts`**
- Add to `VM`: `iso_path: string | null`, `vrde_enabled: boolean`, `vrde_port: number | null`

**`frontend/components/vm-card.tsx`**
- Info section: show `ISO: <filename>` if `vm.iso_path` (use `basename`); show `RDP :<port>` if `vm.vrde_enabled`
- Attach ISO: button that reveals an `<input>` for path → calls `POST /api/v1/vm/iso`
- Detach ISO: button visible when `iso_path != null && status === "stopped"`
- Enable VRDE: button that reveals a port `<input>` → calls `POST /api/v1/vm/vrde`
- Disable VRDE: button visible when `vrde_enabled && status === "stopped"`
- New action props: `onAttachISO`, `onDetachISO`, `onEnableVRDE`, `onDisableVRDE`
- All 4 disabled when `loading || status !== "stopped"`

**Done when**: `tsc --noEmit` passes; card renders without errors.

---

## T008 — Frontend: auto-polling

**`frontend/components/vms-client.tsx`** and **`frontend/components/admin-vms-client.tsx`**:

Add after existing `useState` declarations:
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

Also wire up the 4 new ISO/VRDE handlers in `vms-client.tsx` and `admin-vms-client.tsx`.

**Done when**: Starting a VM causes card to update to `running` without Sync; no memory leak in console.

---

## T009 — Verify

```bash
cd backend && ruff check . && pytest
cd ../frontend && npx tsc --noEmit
```

All must pass with zero errors and zero regressions.
