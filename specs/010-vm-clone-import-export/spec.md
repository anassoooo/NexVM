# Spec 010 — VM Clone, Import & Export OVA

**Branch**: main  
**Created**: 2026-04-30  
**Status**: Draft

---

## Goal

Add three VirtualBox operations that enable VM portability and duplication:

- **Clone VM** — create an identical copy of a stopped VM with a new name
- **Export OVA** — export a stopped VM to an `.ova` file on disk
- **Import OVA** — import an `.ova` / `.ovf` file as a new VM registered in the system

---

## Scope

### In scope
- `POST /api/v1/vm/clone` — clone a stopped VM
- `POST /api/v1/vm/export` — export a stopped VM to an OVA path
- `POST /api/v1/vm/import` — import an OVA/OVF file as a new VM

### Out of scope
- Linked clones (full clone only — simpler, no snapshot dependency)
- Exporting to remote storage / S3
- Progress tracking (VBoxManage export/import can take minutes — out of MVP scope)
- Admin-specific clone/import/export routes (user routes sufficient)

---

## VBoxManage Commands

```bash
# Clone
VBoxManage clonevm <name|uuid> --name <new-name> --register

# Export
VBoxManage export <name|uuid> --output <path.ova>

# Import
VBoxManage import <path.ova|.ovf> --vsys 0 --vmname <name> --memory <mb> --cpus <n>
```

---

## State Rules

| Operation | Allowed VM states | Result |
|---|---|---|
| clone_vm  | stopped, error    | new VM row with status=stopped |
| export_ova | stopped          | file written to disk, VM unchanged |
| import_ova | — (no source VM) | new VM row with status=stopped |

---

## Security Constraints

- `clone_vm`: new name validated same as `create_vm` (regex + quota check)
- `export_ova`: output path must be absolute, end with `.ova`, parent dir must exist
- `import_ova`: source path must be absolute, end with `.ova` or `.ovf`, file must exist
- All three added to `VBOXMANAGE_COMMANDS` whitelist (`clonevm`, `export`, `import`)

---

## DB Changes

No new tables or columns required.

- `clone_vm` → inserts a new row in `vms` (same pattern as `create_vm`)
- `import_ova` → inserts a new row in `vms`
- `export_ova` → no DB write (file-only operation)
- New `LogAction` values: `clone_vm`, `import_vm`, `export_vm`

---

## API Contracts

### POST /api/v1/vm/clone
```json
Request:  { "vm_id": "<uuid>", "new_name": "<name>" }
Response: VMResponse (201)
Errors:   404 (vm not found), 409 (not stopped | name conflict | quota exceeded)
```

### POST /api/v1/vm/export
```json
Request:  { "vm_id": "<uuid>", "output_path": "/exports/my-vm.ova" }
Response: { "message": "Exported to /exports/my-vm.ova" }
Errors:   404, 409 (not stopped), 422 (bad path)
```

### POST /api/v1/vm/import
```json
Request:  { "source_path": "/imports/ubuntu.ova", "name": "<vm-name>", "ram": 1024, "cpu": 2 }
Response: VMResponse (201)
Errors:   409 (quota exceeded | name conflict), 422 (file not found | bad ext)
```

---

## Frontend Changes

- `vm-card.tsx`: add **Clone** button (stopped/error state) + **Export** button (stopped state) with inline output-path input
- `vms-client.tsx`: global **Import OVA** button in header area + modal/inline form
- Propagate handlers through `vm-list.tsx`, `vms-client.tsx`, `admin-vms-client.tsx`
