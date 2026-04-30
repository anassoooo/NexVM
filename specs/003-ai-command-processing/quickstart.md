# Quickstart & Smoke Tests: AI Command Processing

**Branch**: `003-ai-command-processing` | **Date**: 2026-04-07

---

## Prerequisites

- Backend running: `cd backend && uvicorn app.main:app --reload`
- Frontend running: `cd frontend && npm run dev`
- `GROQ_API_KEY` set in `backend/.env`
- At least one user account exists (sign up via `/signup` if needed)
- VBoxManage reachable on host (for full end-to-end; mocked in tests)

---

## Backend Unit Tests

```bash
cd backend
pytest tests/test_ai_service.py -v
```

Expected: **13 passed**.

```bash
pytest -q
```

Expected: **34 passed** (all tests including vm_service and auth).

---

## Smoke Tests (Manual End-to-End)

### 1. AI page auth redirect

- Navigate to `http://localhost:3000/ai` while logged out
- **Expected**: Redirect to `/login`

### 2. AI page loads

- Log in, navigate to `/ai`
- **Expected**: Chat UI renders with placeholder text and empty message list

### 3. Navigation

- **Expected**: "AI" link visible in navbar, navigates to `/ai`

### 4. Create VM via AI

- Type: `create an Ubuntu VM with 2GB RAM called smoke-test`
- Click Send
- **Expected**: "Thinking..." appears, then assistant message: "Created VM 'smoke-test'" with `create_vm` badge
- Navigate to `/vms` — **Expected**: `smoke-test` VM appears with "stopped" status

### 5. Start VM via AI

- Go back to `/ai`
- Type: `start smoke-test`
- **Expected**: Assistant confirms VM started; `/vms` shows status "running"

### 6. Stop VM via AI

- Type: `stop smoke-test`
- **Expected**: Assistant confirms VM stopped; `/vms` shows status "stopped"

### 7. Delete VM via AI

- Type: `delete smoke-test`
- **Expected**: Assistant confirms VM deleted; `/vms` shows VM removed

### 8. Unrecognized command

- Type: `what is the weather today`
- **Expected**: Error message in red — AI could not understand the command; no VM action taken

### 9. Invalid parameters

- Type: `create a VM with 999999 MB of RAM`
- **Expected**: Error message — AI returned invalid parameters (RAM out of range)

### 10. Rate limit

- Send 10 commands rapidly (any valid or invalid commands)
- Send an 11th command
- **Expected**: Error message — "Rate limit exceeded — max 10 AI commands per minute"

### 11. Audit log check

- After running smoke tests 4–7, check Supabase `ai_usage` table:
  - **Expected**: 4+ records with correct user_id, prompts, and token counts

- Check `logs` table:
  - **Expected**: 4+ records with `action = 'ai_command'` and appropriate success/failure status

---

## API Smoke Test (curl)

```bash
# Get JWT from browser DevTools (Application → Local Storage → supabase.auth.token)
TOKEN="<paste-jwt-here>"

curl -X POST http://localhost:8000/api/v1/ai/command \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "create a Debian VM with 1GB RAM called curl-test"}'
```

**Expected response**:
```json
{
  "action": "create_vm",
  "result": "Created VM 'curl-test'",
  "ai_response": {
    "action": "create_vm",
    "name": "curl-test",
    "os": "Debian",
    "ram": 1024
  }
}
```

---

## All Passing = Feature Complete

All 11 smoke tests passing + 13 pytest tests passing = spec 003 complete.
