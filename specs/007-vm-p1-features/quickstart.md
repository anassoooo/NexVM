# Quickstart — Spec 007 VM P1 Features

## Prerequisites

- VirtualBox installed, `VBoxManage` reachable
- At least one ISO file on the host (e.g. `C:\ISOs\ubuntu-22.04.iso`)
- Backend running: `cd backend && uvicorn app.main:app --reload`

---

## Smoke tests

### F1 — ISO attach/detach

```bash
# Attach ISO to a stopped VM
curl -X POST http://localhost:8000/api/v1/vm/iso \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"vm_id": "<uuid>", "iso_path": "C:\\ISOs\\ubuntu-22.04.iso"}'
# → VMResponse with iso_path set

# Detach ISO
curl -X DELETE http://localhost:8000/api/v1/vm/iso \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"vm_id": "<uuid>"}'
# → VMResponse with iso_path: null

# Error: VM not stopped
# → HTTP 409

# Error: path does not exist
curl -X POST http://localhost:8000/api/v1/vm/iso \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"vm_id": "<uuid>", "iso_path": "C:\\nonexistent.iso"}'
# → HTTP 422
```

### F2 — VRDE enable/disable

```bash
# Enable VRDE on port 3389
curl -X POST http://localhost:8000/api/v1/vm/vrde \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"vm_id": "<uuid>", "port": 3389}'
# → VMResponse with vrde_enabled: true, vrde_port: 3389

# Disable VRDE
curl -X DELETE http://localhost:8000/api/v1/vm/vrde \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"vm_id": "<uuid>"}'
# → VMResponse with vrde_enabled: false, vrde_port: null

# Error: port conflict
# → HTTP 409 "Port already in use by another VM"
```

### F3 — Auto-polling (frontend)

1. Open the admin VMs page (`/admin/vms`)
2. Click **Start** on a stopped VM
3. Observe: status changes to `starting` immediately (optimistic update)
4. Wait 5–10s — status changes to `running` automatically without clicking Sync
5. Open browser DevTools → Network tab → confirm periodic `GET /api/v1/vm` requests
6. After all VMs are stable — confirm the periodic requests stop

---

## Run tests

```bash
cd backend
pytest tests/test_vm_p1_service.py -v
pytest -q   # full suite — no regressions
```
