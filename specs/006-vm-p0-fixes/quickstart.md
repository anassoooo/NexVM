# Quickstart — Spec 006 P0 Bug Fixes

## Verification after fixes

```bash
# 1. Lint
cd backend && ruff check .

# 2. Tests
pytest

# 3. Manual smoke test (backend running)
# Login and send an AI command:
curl -X POST http://localhost:8000/api/v1/ai/command \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "list my vms"}'

# Should return user's VMs only — no TypeError

curl -X POST http://localhost:8000/api/v1/ai/command \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "create a vm called test with ubuntu 22.04 4 cores and 4gb ram"}'

# Should pass cpu=4, ram=4096 to VBoxManage

# 4. Admin route smoke test
curl -X POST http://localhost:8000/api/v1/admin/vm/start \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{"vm_id": "<uuid>"}'

# Should not crash on UUID→str conversion
```
