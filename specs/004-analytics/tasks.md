# Tasks: Analytics

**Feature Branch**: `004-analytics`
**Depends on**: `003-ai-command-processing` complete — `ai_usage`, `vms`, `profiles` tables populated; `get_current_admin_user` dependency in place.
**Source**: [spec.md](spec.md), [plan.md](plan.md)

---

## Phase 1: Setup

- [ ] T001 Create branch `004-analytics` from main; verify 003 dependencies pass: `pytest -q` green, `ai_usage` + `vms` + `profiles` tables queryable in Supabase.

---

## Phase 2: Foundational

- [ ] T002 [P] Add analytics Pydantic schemas to `backend/app/models/schemas.py`:
  `UserAnalytics(total_vms, running_vms, stopped_vms, error_vms, total_ai_commands)` and `AdminAnalytics` extending it with `total_users`. Add `AIQueryAnalytics(action="query_analytics", scope: Literal["user","admin"])` for AI command dispatch.

- [ ] T003 [P] Add TypeScript interfaces to `frontend/types/index.ts`:
  `UserAnalytics { total_vms, running_vms, stopped_vms, error_vms, total_ai_commands }` and `AdminAnalytics { total_users, total_vms, running_vms, stopped_vms, error_vms, total_ai_commands }`.

---

## Phase 3: US1 — AI Chat VM Summary (P1)

> Regular user loads `/ai`, AI greeting shows VM status summary (total, running, stopped, error). Replaces removed `/dashboard`. Fallback to generic welcome on API failure.

### Backend

- [ ] T004 Create `backend/app/services/analytics_service.py`:
  `get_user_analytics(user_id)` queries `vms` by user_id (count by status in Python) and `ai_usage` by user_id (row count). Wraps exceptions in `HTTPException(500, "Analytics unavailable")`.

- [ ] T005 Create `backend/app/routes/analytics.py`:
  `GET /` with `Depends(get_current_user)` → `analytics_service.get_user_analytics(user_id)`, returns `UserAnalytics`.

- [ ] T006 Update `backend/app/main.py`: import and include analytics router at `prefix="/api/v1/analytics"`.

- [ ] T007 Update `backend/app/services/ai_service.py`:
  Add `"query_analytics"` to `ALLOWED_ACTIONS` and `ACTION_SCHEMAS`. Implement `_execute_action` branch: scope=`"user"` calls `analytics_service.get_user_analytics`, returns natural-language VM summary; scope=`"admin"` checks `is_admin` then calls `analytics_service.get_admin_analytics`. Update `SYSTEM_PROMPT` with `query_analytics` action description.

### Frontend

- [ ] T008 Update `frontend/components/ai-chat.tsx`:
  Add `useEffect` on mount that calls `GET /api/v1/analytics` and sets the initial assistant message to a VM status greeting (total, running, stopped, error counts — no AI command count). On API failure, fall back to generic `"Welcome! What would you like to do?"`. Import `UserAnalytics` from `@/types`.

**Checkpoint US1**: Open `/ai` as a user with mixed-status VMs → AI greeting shows correct counts. With no VMs → shows "You have 0 VMs". Kill backend → generic welcome, no crash.

---

## Phase 4: US2 — Admin System Metrics (P1)

> Admin visits `/admin`, sees system-wide metrics (total users, total VMs, status breakdown, total AI commands). Non-admin redirected to `/ai`.

### Backend

- [ ] T009 In `backend/app/services/analytics_service.py`: add `get_admin_analytics()` — queries `profiles` (total users), `vms` all rows (count by status), `ai_usage` all rows (total commands). Returns `AdminAnalytics`.

- [ ] T010 In `backend/app/routes/analytics.py`: add `GET /admin` with `Depends(get_current_admin_user)` → `analytics_service.get_admin_analytics()`, returns `AdminAnalytics`. Non-admin gets 403.

### Frontend

- [ ] T011 Update `frontend/app/admin/page.tsx`:
  Replace `[placeholder]` with live metrics fetched from `GET /api/v1/analytics/admin` using session token. Render two rows: System Summary (Total Users, Total VMs, Total AI Commands) and VM Status (Running, Stopped, Error). On fetch failure or `null` analytics, display "—" instead of crashing. Keep existing auth+admin guard (non-admin → redirect to `/ai`).

**Checkpoint US2**: Admin sees `/admin` with correct system counts matching Supabase. Non-admin gets redirected to `/ai`. Direct API call by non-admin → 403.

---

## Phase 5: Tests & Polish

- [ ] T012 Create `backend/tests/test_analytics_service.py` with 8 test cases (mocked Supabase):
  - User: (1) correct VM status counts, (2) correct AI command count, (3) all zeros for empty user
  - Admin: (4) correct total_users, (5) correct VM counts, (6) correct total_ai_commands
  - Auth: (7) non-admin → 403 on `/admin`, (8) no token → 401 on `/`

- [ ] T013 Run `pytest -q` — all backend tests pass, zero regressions from prior specs.

- [ ] T014 Run `tsc --noEmit` in `frontend/` — zero TypeScript errors after adding analytics types.

- [ ] T015 Verify graceful degradation: `/admin` shows "—" when analytics API returns error; `/ai` shows generic greeting when analytics API is unreachable — no crashes.

- [ ] T016 Verify `GET /api/v1/analytics/admin` returns 403 for non-admin authenticated user (SC-003).

- [ ] T017 Smoke-test: user with N VMs → AI opening message on `/ai` contains correct total + status breakdown; AI command count absent from greeting (SC-001).

---

## Dependencies

```text
T001 (branch)
  → T002 [P], T003 [P]              (schemas + types, parallel)
  → T004 (service) → T005 (route) → T006 (main.py) → T007 (ai_service)
  → T008 (ai-chat greeting)         (needs T005 API available)
  → T009 (admin service) → T010 (admin route)
  → T011 (admin page)               (needs T010 API available)
  → T012–T017 (tests + polish)      (needs all prior phases)
```

**Total: 17 tasks** across 5 phases.
