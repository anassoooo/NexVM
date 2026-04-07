# Tasks: Analytics

**Input**: Design documents from `/specs/004-analytics/`  
**Prerequisites**: `003-ai-command-processing` complete ✅ — `ai_usage` table populated, `vms` and `profiles` tables exist, `get_current_admin_user` dependency in place.

**Tests**: Backend unit tests for analytics_service.py with mocked Supabase client.

**Organization**: Backend must be complete before frontend integration.

## Format: `[ID] [P?] Description`

- **[P]**: Can run in parallel (different files, no shared dependencies)

---

## Phase 1: Backend

**Purpose**: Implement Pydantic schemas, analytics service, and HTTP routes.

- [x] T001 Add analytics schemas to `backend/app/models/schemas.py`:
  - `UserAnalytics(total_vms, running_vms, stopped_vms, error_vms, total_ai_commands)`
  - `AdminAnalytics(total_users, total_vms, running_vms, stopped_vms, error_vms, total_ai_commands)`

- [x] T002 Create `backend/app/services/analytics_service.py`:
  - `get_user_analytics(user_id: str) -> UserAnalytics`
    - query `vms` by user_id → count by status in Python
    - query `ai_usage` by user_id → `len(result.data)`
  - `get_admin_analytics() -> AdminAnalytics`
    - query `profiles` → `len(result.data)` = total_users
    - query `vms` (all) → count by status in Python
    - query `ai_usage` (all) → `len(result.data)` = total_ai_commands
  - Both functions wrap exceptions in `HTTPException(500, "Analytics unavailable")`

- [x] T003 Create `backend/app/routes/analytics.py`:
  - `GET /` → `Depends(get_current_user)` → `analytics_service.get_user_analytics(user_id)`
  - `GET /admin` → `Depends(get_current_admin_user)` → `analytics_service.get_admin_analytics()`

- [x] T004 Update `backend/app/main.py`:
  - Import and include analytics router at `/api/v1/analytics`

**Checkpoint**: `GET /api/v1/analytics` and `GET /api/v1/analytics/admin` appear in `/docs`.

---

## Phase 2: Backend Tests

**Purpose**: Verify analytics service paths using mocked Supabase client.

- [x] T005 Create `backend/tests/test_analytics_service.py` with 8 test cases:

  **User analytics**:
  - (1) correct VM status counts (mix of running/stopped/error)
  - (2) correct AI command count
  - (3) all zeros when user has no VMs or AI usage

  **Admin analytics**:
  - (4) correct total_users
  - (5) correct VM counts across all users
  - (6) correct total_ai_commands

  **Auth**:
  - (7) `GET /api/v1/analytics/admin` — non-admin user gets 403
  - (8) `GET /api/v1/analytics` — no token gets 403

**Checkpoint**: `pytest tests/test_analytics_service.py -v` — all 8 pass; `pytest -q` — no regressions.

---

## Phase 3: Frontend

**Purpose**: Replace placeholder content with live stat cards.

- [x] T006 [P] Add analytics types to `frontend/types/index.ts`:
  - `UserAnalytics` interface
  - `AdminAnalytics` interface

- [x] T007 Update `frontend/app/dashboard/page.tsx`:
  - Fetch `GET /api/v1/analytics` with session token after auth check
  - Replace "Your virtual machines will appear here" with stat cards
  - Cards: Total VMs | Running | Stopped | Errors | AI Commands
  - Fallback to `null` on fetch failure → display "—"

- [x] T008 Update `frontend/app/admin/page.tsx`:
  - Fetch `GET /api/v1/analytics/admin` with session token after admin guard
  - Replace `[placeholder]` with system summary row + VM status row
  - Summary: Total Users | Total VMs | Total AI Commands
  - VM status: Running | Stopped | Error

**Checkpoint**: `/dashboard` shows live VM counts; `/admin` shows system-wide stats.

---

## Dependencies & Execution Order

```text
Phase 1 (Backend)
    T001 (schemas) → T002 (analytics_service) → T003 (route) → T004 (main.py)
    ↓
Phase 2 (Backend Tests)
    ↓
Phase 3 (Frontend)
    T006 [P] + T007 [P] + T008 [P]  ← all independent once Phase 1 is done
```

### Within Phase 1
```
T001 → T002 → T003 → T004
```

### Within Phase 3
```
T006, T007, T008  (all parallel — different files)
```
