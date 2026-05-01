# Tasks — Spec 010: VM Clone, Import & Export OVA

**Total**: 8 tasks

---

## T001 — Enums & Schemas

**File**: `backend/app/models/enums.py`, `backend/app/models/schemas.py`

- `LogAction`: add `clone_vm`, `import_vm`, `export_vm`
- New schemas:
  - `VMCloneRequest(vm_id, new_name)`
  - `OVAExportRequest(vm_id, output_path)` — validator: absolute path, ends `.ova`, parent dir exists
  - `OVAImportRequest(source_path, name, ram, cpu)` — validator: absolute path, ends `.ova`/`.ovf`, file exists
  - `OVAExportResponse(message: str)`

---

## T002 — VBoxManage Whitelist

**File**: `backend/app/services/vbox_wrapper.py`

- Add `"clonevm"`, `"export"`, `"import"` to `VBOXMANAGE_COMMANDS`

---

## T003 — Service: clone_vm

**File**: `backend/app/services/vm_service.py`

```
clone_vm(vm_id, new_name, user_id):
  1. _get_vm_or_404(vm_id, user_id) → assert status in (stopped, error) else 409
  2. quota check (same as create_vm)
  3. name uniqueness check in vms table for this user
  4. run_vbox_command(["clonevm", source.vbox_id, "--name", new_name, "--register"])
  5. parse new UUID from stdout (same pattern as create_vm)
  6. insert new row in vms (status=stopped, copy os/ram/cpu/disk_size)
  7. log clone_vm success/failure
  8. return VMResponse
```

---

## T004 — Service: export_ova

**File**: `backend/app/services/vm_service.py`

```
export_ova(vm_id, output_path, user_id):
  1. _get_vm_or_404(vm_id, user_id) → assert status == stopped else 409
  2. run_vbox_command(["export", vm.vbox_id, "--output", output_path])
  3. log export_vm success/failure
  4. return {"message": f"Exported to {output_path}"}
```

---

## T005 — Service: import_ova

**File**: `backend/app/services/vm_service.py`

```
import_ova(source_path, name, ram, cpu, user_id):
  1. quota check
  2. name uniqueness check
  3. run_vbox_command(["import", source_path, "--vsys", "0",
       "--vmname", name, "--memory", str(ram), "--cpus", str(cpu)])
  4. parse UUID from stdout
  5. insert new row in vms (status=stopped, disk_size=20480 default)
  6. log import_vm success/failure
  7. return VMResponse
```

---

## T006 — Routes

**File**: `backend/app/routes/vm.py`

- `POST /clone` → `clone_vm`, returns VMResponse 201
- `POST /export` → `export_ova`, returns OVAExportResponse 200
- `POST /import` → `import_ova`, returns VMResponse 201

---

## T007 — Tests

**File**: `backend/tests/test_vm_p3_service.py`

Tests:
- `test_clone_vm_ok` — success path, new VM returned
- `test_clone_vm_not_stopped` — 409
- `test_clone_vm_quota_exceeded` — 409
- `test_export_ova_ok` — success path
- `test_export_ova_not_stopped` — 409
- `test_import_ova_ok` — success path, new VM returned
- `test_import_ova_quota_exceeded` — 409

---

## T008 — Frontend

**Files**: `frontend/components/vm-card.tsx`, `vm-list.tsx`, `vms-client.tsx`, `admin-vms-client.tsx`

- `vm-card.tsx`:
  - **Clone** button (visible when stopped/error): inline input for new name → calls `onClone(newName)`
  - **Export** button (visible when stopped): inline input for output path → calls `onExport(outputPath)`
- `vm-list.tsx`: add `onClone`, `onExport` props; propagate to VMCard
- `vms-client.tsx`:
  - `handleClone(id, newName)`, `handleExport(id, outputPath)`
  - **Import OVA** button in header → inline form (source_path, name, ram, cpu) → `handleImport`
- `admin-vms-client.tsx`: same handlers as vms-client (no admin-specific routes needed)
