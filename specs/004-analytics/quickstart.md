# Quickstart & Smoke Tests: Analytics

**Branch**: `004-analytics` | **Date**: 2026-04-07

---

## Prerequisites

- Backend running: `cd backend && uvicorn app.main:app --reload`
- Frontend running: `cd frontend && npm run dev`
- At least one user account exists with some VMs (create via `/vms` if needed)
- Admin user exists (`profiles.is_admin = true` set in Supabase)

---

## Backend Unit Tests

```bash
cd backend
pytest tests/test_analytics_service.py -v
```

Expected: **8 passed**.

```bash
pytest -q
```

Expected: **all passed** (no regressions).

---

## Smoke Tests (Manual End-to-End)

### 1. User analytics endpoint

```bash
TOKEN="<paste-jwt-here>"
curl http://localhost:8000/api/v1/analytics \
  -H "Authorization: Bearer $TOKEN"
```

**Expected**:
```json
{
  "total_vms": 2,
  "running_vms": 1,
  "stopped_vms": 1,
  "error_vms": 0,
  "total_ai_commands": 3
}
```

### 2. Admin endpoint — non-admin gets 403

Use a non-admin JWT:
```bash
curl http://localhost:8000/api/v1/analytics/admin \
  -H "Authorization: Bearer $NON_ADMIN_TOKEN"
```

**Expected**: HTTP 403 `{"detail": "Admin access required"}`

### 3. Admin endpoint — admin gets system metrics

```bash
curl http://localhost:8000/api/v1/analytics/admin \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

**Expected**:
```json
{
  "total_users": 1,
  "total_vms": 2,
  "running_vms": 1,
  "stopped_vms": 1,
  "error_vms": 0,
  "total_ai_commands": 3
}
```

### 4. Dashboard shows live counts

- Log in, navigate to `/dashboard`
- **Expected**: Stat cards show Total VMs, Running, Stopped, Errors, AI Commands — matching the values from step 1

### 5. Dashboard with no VMs

- Log in as a new user with no VMs
- **Expected**: All counts show 0 — page does not crash

### 6. Admin page shows system metrics

- Log in as admin, navigate to `/admin`
- **Expected**: System summary row (Total Users, Total VMs, AI Commands) and VM status row (Running, Stopped, Error) — no `[placeholder]` text

### 7. Non-admin redirected from admin page

- Log in as non-admin, navigate to `/admin`
- **Expected**: Redirect to `/dashboard`

### 8. Unauthenticated API call

```bash
curl http://localhost:8000/api/v1/analytics
```

**Expected**: HTTP 401 (HTTPBearer returns 401 for missing token — matches `test_analytics_no_token_rejected`)

---

## All Passing = Feature Complete

All 8 smoke tests passing + 8 pytest tests passing = spec 004 complete.
