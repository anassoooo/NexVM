# Quickstart — Spec 008 VM P2 Lifecycle

## Smoke tests

### F1 — Modify VM
```bash
curl -X POST http://localhost:8000/api/v1/vm/modify \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"vm_id": "<uuid>", "ram": 4096, "cpu": 4}'
# → VMResponse with ram: 4096, cpu: 4
```

### F2 — Pause / Resume
```bash
curl -X POST http://localhost:8000/api/v1/vm/pause \
  -H "Authorization: Bearer <token>" \
  -d '{"vm_id": "<uuid>"}'
# → VMResponse with status: "paused"

curl -X POST http://localhost:8000/api/v1/vm/resume \
  -H "Authorization: Bearer <token>" \
  -d '{"vm_id": "<uuid>"}'
# → VMResponse with status: "running"
```

### F3 — Save State
```bash
curl -X POST http://localhost:8000/api/v1/vm/savestate \
  -H "Authorization: Bearer <token>" \
  -d '{"vm_id": "<uuid>"}'
# → VMResponse with status: "stopped"
# Starting VM again restores from saved state (VirtualBox behavior)
```

### F4 — Port-forwarding
```bash
# Add rule
curl -X POST http://localhost:8000/api/v1/vm/portfwd \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"vm_id": "<uuid>", "name": "http", "protocol": "tcp", "host_port": 8080, "guest_port": 80}'
# → VMResponse with nat_rules: [{...}]

# Remove rule
curl -X DELETE http://localhost:8000/api/v1/vm/portfwd \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"vm_id": "<uuid>", "name": "http"}'
```

### F5 — Snapshots
```bash
# Take
curl -X POST http://localhost:8000/api/v1/vm/snapshot \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"vm_id": "<uuid>", "name": "clean-install", "description": "Fresh Ubuntu install"}'
# → SnapshotResponse

# List
curl http://localhost:8000/api/v1/vm/snapshots?vm_id=<uuid> \
  -H "Authorization: Bearer <token>"
# → [SnapshotResponse, ...]

# Restore
curl -X POST http://localhost:8000/api/v1/vm/snapshot/restore \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"vm_id": "<uuid>", "name": "clean-install"}'

# Delete
curl -X DELETE http://localhost:8000/api/v1/vm/snapshot \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"vm_id": "<uuid>", "name": "clean-install"}'
```

## Run tests
```bash
cd backend
pytest tests/test_vm_p2_service.py -v
pytest -q   # full suite — no regressions
```
