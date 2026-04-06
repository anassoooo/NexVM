# Quickstart: VM Management

**Branch**: `002-vm-management` | **Date**: 2026-04-06

This guide verifies the VM management feature end-to-end. Complete `001-supabase-auth-db` quickstart first — auth, schema, and a working backend/frontend are prerequisites.

---

## Prerequisites

- `001-supabase-auth-db` complete and smoke-tested
- VirtualBox installed on the machine running the backend
- `VBoxManage --version` returns a version string (not "command not found")
- Backend running on `http://localhost:8000`
- Frontend running on `http://localhost:3000`
- Logged-in user session available (from spec 001 setup)

---

## Step 1 — Verify VBoxManage is Reachable

```bash
VBoxManage --version
# Expected: something like "7.0.14r161095"

VBoxManage list vms
# Expected: empty output or existing VMs — no error
```

If `VBoxManage` is not on PATH, set `VBOXMANAGE_PATH` in `backend/.env` to the full binary path (e.g., `C:\Program Files\Oracle\VirtualBox\VBoxManage.exe` on Windows).

---

## Step 2 — Confirm Health Endpoint Reports VBoxManage

```bash
curl http://localhost:8000/api/v1/health
```

Expected response:

```json
{
  "status": "ok",
  "vboxmanage": "7.0.14r161095"
}
```

If `vboxmanage` shows an error string instead of a version, fix the PATH/VBOXMANAGE_PATH before proceeding.

---

## Step 3 — Get a JWT Token

```bash
# Log in via the frontend or directly via Supabase:
curl -X POST https://<your-project>.supabase.co/auth/v1/token?grant_type=password \
  -H "apikey: <SUPABASE_ANON_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"email": "your@email.com", "password": "yourpassword"}'
```

Copy the `access_token` from the response. Use it as `<JWT>` in the steps below.

---

## Step 4 — Create a VM

```bash
curl -X POST http://localhost:8000/api/v1/vm/create \
  -H "Authorization: Bearer <JWT>" \
  -H "Content-Type: application/json" \
  -d '{"name": "test-vm-01", "os": "Ubuntu 22.04", "ram": 1024}'
```

Expected response (HTTP 201):

```json
{
  "id": "<uuid>",
  "user_id": "<user-uuid>",
  "name": "test-vm-01",
  "os": "Ubuntu 22.04",
  "ram": 1024,
  "status": "stopped",
  "error_message": null,
  "created_at": "...",
  "updated_at": "..."
}
```

Verify in VirtualBox:

```bash
VBoxManage list vms
# Expected: "test-vm-01" {<uuid>}
```

---

## Step 5 — List VMs

```bash
curl http://localhost:8000/api/v1/vm \
  -H "Authorization: Bearer <JWT>"
```

Expected: JSON array containing the VM created in Step 4 with `"status": "stopped"`.

---

## Step 6 — Start the VM

```bash
curl -X POST http://localhost:8000/api/v1/vm/start \
  -H "Authorization: Bearer <JWT>" \
  -H "Content-Type: application/json" \
  -d '{"vm_id": "<uuid-from-step-4>"}'
```

Expected response (HTTP 200):

```json
{ ..., "status": "running", "error_message": null }
```

Verify in VirtualBox:

```bash
VBoxManage showvminfo test-vm-01 --machinereadable | grep VMState
# Expected: VMState="running"
```

---

## Step 7 — Stop the VM

```bash
curl -X POST http://localhost:8000/api/v1/vm/stop \
  -H "Authorization: Bearer <JWT>" \
  -H "Content-Type: application/json" \
  -d '{"vm_id": "<uuid-from-step-4>"}'
```

Expected response (HTTP 200):

```json
{ ..., "status": "stopped", "error_message": null }
```

---

## Step 8 — Delete the VM

```bash
curl -X POST http://localhost:8000/api/v1/vm/delete \
  -H "Authorization: Bearer <JWT>" \
  -H "Content-Type: application/json" \
  -d '{"vm_id": "<uuid-from-step-4>"}'
```

Expected response (HTTP 200):

```json
{ "detail": "VM deleted" }
```

Verify in VirtualBox:

```bash
VBoxManage list vms
# Expected: "test-vm-01" no longer listed
```

Verify in database:

```sql
-- Run in Supabase SQL Editor
SELECT * FROM vms WHERE name = 'test-vm-01';
-- Expected: 0 rows
```

---

## Step 9 — Check Logs

```sql
-- Run in Supabase SQL Editor
SELECT action, target, status, message, created_at
FROM logs
ORDER BY created_at DESC
LIMIT 10;
```

Expected: Four log rows for `create_vm`, `start_vm`, `stop_vm`, `delete_vm` — all with `status = 'success'`.

---

## Step 10 — Run Backend Tests

```bash
cd backend
pytest tests/test_vm_service.py -v
```

All tests should pass.

---

## Step 11 — Frontend Smoke Test

1. Navigate to `http://localhost:3000/vms` — empty state shown ("No VMs yet")
2. Click **Create VM** → fill in name, OS, RAM → submit → VM appears with "stopped" badge
3. Click **Start** → badge changes to "starting" then "running"
4. Click **Stop** → badge changes to "stopping" then "stopped"
5. Click **Delete** → confirm → VM disappears from list
6. Check `/vms` — empty state shown again

---

## Troubleshooting

| Symptom | Check |
|---|---|
| `503 VBoxManage not reachable` | Verify `VBoxManage --version` works; set `VBOXMANAGE_PATH` in backend `.env` |
| `409 A VM with this name already exists` | Run `VBoxManage list vms` — name is already registered; use a different name |
| `409 VM is already in a transitional state` | Wait a moment and retry; a previous operation may still be running |
| `404 VM not found` | Confirm the `vm_id` UUID belongs to the currently logged-in user |
| VM stuck in "starting" | VBoxManage may have failed silently; check `error_message` field; run `VBoxManage showvminfo <name>` |
| Log rows missing after action | Check if `SUPABASE_SERVICE_KEY` is set — logs use the service role client |
| Frontend shows stale status | Page refetches after each action; hard reload (`Ctrl+Shift+R`) if data looks stale |
