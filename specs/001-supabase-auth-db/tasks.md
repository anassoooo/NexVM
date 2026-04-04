# Tasks: Supabase Auth & Database Setup

**Input**: Design documents from `/specs/001-supabase-auth-db/`  
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Tests**: Included for the backend auth layer only (`test_auth.py`) — as required by the spec's Testing Strategy section.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on each other)
- **[Story]**: Which user story this task belongs to (US1–US4)

---

## Phase 1: Setup (Project Structure)

**Purpose**: Create the physical directory layout and stub files so later tasks have clear targets. No logic — scaffolding only.

- [x] T001 Create `backend/app/routes/`, `backend/app/services/`, `backend/app/models/`, `backend/app/utils/`, `backend/tests/` directories with empty `__init__.py` files
- [x] T002 Initialize Next.js 14 project in `frontend/` via `npx create-next-app@14 frontend --typescript --tailwind --app --no-src-dir`
- [x] T003 Create `supabase/migrations/` directory at repo root
- [x] T004 [P] Create `backend/requirements.txt` with: `fastapi`, `uvicorn[standard]`, `supabase`, `python-jose[cryptography]`, `pydantic-settings`, `httpx`, `groq`, `pytest`, `pytest-asyncio`
- [x] T005 [P] Create `backend/.env.example` with keys: `SUPABASE_URL`, `SUPABASE_KEY`, `SUPABASE_SERVICE_KEY`, `SUPABASE_JWT_SECRET`, `GROQ_API_KEY`, `FRONTEND_URL`, `VBOXMANAGE_PATH`
- [x] T006 [P] Create `frontend/.env.example` with keys: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `NEXT_PUBLIC_API_URL`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Database schema + Supabase project configuration. **Nothing else can be built until this phase is complete** — all user stories depend on the schema and auth settings being live.

**⚠️ CRITICAL**: Complete and verify every task in this phase before starting Phase 3.

- [ ] T007 Copy `specs/001-supabase-auth-db/contracts/schema.sql` to `supabase/migrations/001_initial_schema.sql` — this is the canonical migration file
- [ ] T008 Run `supabase/migrations/001_initial_schema.sql` in Supabase SQL Editor and verify: tables `profiles`, `vms`, `logs`, `ai_usage` exist; RLS enabled on all four; trigger `on_auth_user_created` exists under Database → Triggers
- [ ] T009 Configure Supabase Auth settings in dashboard: JWT expiry = `86400`; minimum password length = `8`; password must contain a number; rate limit email sign-in = 10 per 900 seconds
- [ ] T010 [P] Create `backend/app/config.py` — `Settings` class using `pydantic-settings` loading all vars from `.env`: `SUPABASE_URL`, `SUPABASE_KEY`, `SUPABASE_SERVICE_KEY`, `SUPABASE_JWT_SECRET`, `GROQ_API_KEY`, `FRONTEND_URL`, `VBOXMANAGE_PATH`
- [ ] T011 [P] Create `backend/app/models/enums.py` — `VMStatus` enum with values: `stopped`, `starting`, `running`, `stopping`, `error`; `LogStatus` enum with `success`, `failure`; `LogAction` enum with `create_vm`, `start_vm`, `stop_vm`, `delete_vm`, `login`, `ai_command`
- [ ] T012 [P] Create `backend/app/utils/logger.py` — structured logger helper that outputs JSON lines with fields: `user_id`, `action`, `target`, `status`, `message`, `timestamp` (UTC ISO 8601)

**Checkpoint**: Schema is live in Supabase, auth settings configured, backend config + enums ready. Run `SELECT * FROM profiles;` in SQL Editor — should return empty table with correct columns.

---

## Phase 3: User Story 1 - Register and Access (Priority: P1) 🎯 MVP

**Goal**: A user can sign up, be redirected to the dashboard, and their profile is auto-created. A user can log in and log out. Unauthenticated users are redirected to `/login`.

**Independent Test**: Create a new account → verify `/dashboard` loads → verify `profiles` table has a row → logout → verify redirect to `/login` → navigate to `/dashboard` directly → verify redirect to `/login` again.

### Backend

- [ ] T013 Create `backend/app/dependencies.py` — implement `get_current_user(token = Depends(HTTPBearer())) -> str`: decode HS256 JWT with `python-jose`, validate `aud="authenticated"`, extract `sub` as `user_id`, call `ensure_profile_exists(user_id)`, raise `HTTPException(401)` on any failure. Implement `ensure_profile_exists(user_id)`: query `profiles` by `id`, insert `{id, is_admin: false}` if missing (idempotent fallback per research.md §2)
- [ ] T014 [P] [US1] Create `backend/app/routes/health.py` — `GET /api/v1/health` returns `{"status": "ok", "vboxmanage": "<version or error>"}`. No auth required. Runs `VBoxManage --version` via subprocess (with 5s timeout) to confirm host tool is reachable.
- [ ] T015 [US1] Create `backend/app/main.py` — FastAPI app with: `CORSMiddleware` allowing `settings.FRONTEND_URL` origin only, methods `GET`/`POST`; include health router under `/api/v1`; Supabase client initialized on startup via lifespan; `settings` imported from `config.py`

### Frontend

- [ ] T016 [P] [US1] Create `frontend/lib/supabase/client.ts` — export `createBrowserClient` instance using `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` from `@supabase/ssr`
- [ ] T017 [P] [US1] Create `frontend/lib/supabase/server.ts` — export `createServerClient` factory using `cookies()` from `next/headers`, for use in Server Components and Route Handlers
- [ ] T018 [US1] Create `frontend/middleware.ts` — use `createServerClient` to read session; if no session and route is not under `/(auth)`, redirect to `/login`; export `config.matcher` to cover all routes except `_next/static`, `_next/image`, and `favicon.ico`
- [ ] T019 [P] [US1] Create `frontend/app/(auth)/signup/page.tsx` — form with email + password fields; client-side validation: password ≥ 8 chars + contains number (matches FR-017); on submit call `supabase.auth.signUp()`; on success redirect to `/dashboard`; on error display message
- [ ] T020 [P] [US1] Create `frontend/app/(auth)/login/page.tsx` — form with email + password; on submit call `supabase.auth.signInWithPassword()`; on success redirect to `/dashboard`; on error display message including rate-limit error (HTTP 429) with retry time
- [ ] T021 [US1] Create `frontend/app/layout.tsx` — root layout with Tailwind CSS globals; wrap children with any required providers; include `<Navbar />` stub (can be a simple div for now)
- [ ] T022 [US1] Create `frontend/app/page.tsx` — server component; check session via `createServerClient`; redirect to `/dashboard` if authenticated, `/login` if not
- [ ] T023 [US1] Create `frontend/app/dashboard/page.tsx` — protected server component; reads session via `createServerClient`; renders "Dashboard — welcome, {email}" placeholder; includes a logout button that calls `supabase.auth.signOut()` then redirects to `/login`

### Backend Tests

- [ ] T024 [US1] Create `backend/tests/test_auth.py` — three test cases using `pytest` + `httpx.AsyncClient`: (1) valid unexpired Supabase JWT returns 200 from a protected endpoint; (2) expired JWT returns 401; (3) missing `Authorization` header returns 401. Use `python-jose` to generate test JWTs signed with `SUPABASE_JWT_SECRET` from test env.

**Checkpoint**: Registration, login, logout, and redirect all work end-to-end. `profiles` row appears after signup. `pytest backend/tests/test_auth.py` passes all three cases.

---

## Phase 4: User Story 2 - Session Persistence (Priority: P2)

**Goal**: A logged-in user closes the browser and returns within 24 hours — they are still authenticated. After 24 hours, they are redirected to `/login`. Logout on one device does not affect other devices.

**Independent Test**: Log in, close browser, reopen and navigate to `/dashboard` → still authenticated (within 24h window).

- [ ] T025 [US2] Update `frontend/middleware.ts` — add explicit handling for expired/invalid session: when `supabase.auth.getSession()` returns a session error or null after a previously valid cookie, clear the stale cookie and redirect to `/login` with query param `?reason=session_expired` so the login page can display "Your session has expired, please log in again"
- [ ] T026 [P] [US2] Create `frontend/hooks/use-auth.ts` — client-side hook that calls `supabase.auth.getSession()` and `supabase.auth.onAuthStateChange()`; returns `{ session, user, loading }`; used by client components that need real-time auth state
- [ ] T027 [US2] Update `frontend/app/(auth)/login/page.tsx` — read `?reason=session_expired` query param and display "Your session has expired. Please log in again." above the form when present

**Checkpoint**: Close browser, reopen within session window → still logged in. Log in, wait for session expiry (or test by manually expiring the cookie) → redirected to `/login` with "session expired" message.

---

## Phase 5: User Story 3 - Data Isolation (Priority: P3)

**Goal**: Each user sees only their own VMs, logs, and AI usage. Admin users can see all records. Data isolation is enforced at the database layer.

**Independent Test**: Create two accounts (A and B), insert VM records for each via SQL, log in as A → VM list returns only A's VMs; log in as B → only B's VMs.

- [ ] T028 [P] [US3] Create `backend/app/models/schemas.py` — Pydantic models: `VMCreate` (name: str 1-50, os: str, ram: int 512-16384), `VMResponse` (all VM fields), `LogResponse` (all log fields), `AIUsageResponse` (all ai_usage fields), `UserProfile` (id: str, is_admin: bool). All responses include `id` and `created_at`.
- [ ] T029 [US3] Add `get_current_admin_user` dependency to `backend/app/dependencies.py` — calls `get_current_user` then queries `profiles.is_admin`; raises `HTTPException(403, "Admin access required")` if not admin
- [ ] T030 [US3] Verify RLS isolation manually: in Supabase SQL Editor, run the test queries from `specs/001-supabase-auth-db/data-model.md` — confirm user policy blocks cross-user access and admin policy allows full access. Document result as a comment in `supabase/migrations/001_initial_schema.sql`.

**Checkpoint**: Two accounts created, one querying the other's data returns empty results. Admin account can query all records.

---

## Phase 6: User Story 4 - Admin Role Recognition (Priority: P4)

**Goal**: A user with `is_admin = true` can access `/admin`. A regular user attempting to access `/admin` is redirected or shown access-denied.

**Independent Test**: Manually set `is_admin = true` on a profile, log in as that user → `/admin` loads. Log in as regular user → `/admin` redirects to `/dashboard`.

- [ ] T031 [US4] Update `frontend/middleware.ts` — add admin check for routes under `/admin`: use `createServerClient` to query `profiles.is_admin` for the current user; redirect non-admin users to `/dashboard` with `?reason=access_denied`
- [ ] T032 [P] [US4] Create `frontend/app/admin/page.tsx` — protected server component with admin check; renders "Admin Dashboard — [placeholder]" with current user's email; redirects non-admin to `/dashboard`
- [ ] T033 [P] [US4] Update `frontend/app/dashboard/page.tsx` — add conditional "Admin" navigation link visible only when `profile.is_admin === true`

**Checkpoint**: Admin user reaches `/admin`. Regular user attempting `/admin` is redirected to `/dashboard`.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Deployment readiness and final validation.

- [ ] T034 [P] Create `backend/Dockerfile` — `FROM python:3.12-slim`, copy `requirements.txt`, `pip install`, copy `app/`, `EXPOSE 8000`, `CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]`
- [ ] T035 [P] Create `frontend/types/index.ts` — TypeScript type definitions matching `schemas.py`: `VM`, `Log`, `AIUsage`, `UserProfile`; export all
- [ ] T036 [P] Create `frontend/lib/api.ts` — base API wrapper: inject `Authorization: Bearer <token>` on every request using `supabase.auth.getSession()`; base URL from `NEXT_PUBLIC_API_URL`; typed error handling: extract `detail` from error responses
- [ ] T037 Run every step in `specs/001-supabase-auth-db/quickstart.md` and verify all 7 smoke tests pass. Fix any gaps found.

---

## Dependencies & Execution Order

### Phase Dependencies

```text
Phase 1 (Setup)
    ↓
Phase 2 (Foundational) ← BLOCKS EVERYTHING
    ↓
Phase 3 (US1 — P1) ← MVP stops here
    ↓
Phase 4 (US2 — P2)
    ↓
Phase 5 (US3 — P3) ← can start in parallel with Phase 4 if staffed
    ↓
Phase 6 (US4 — P4)
    ↓
Phase 7 (Polish)
```

### User Story Dependencies

- **US1 (P1)**: Depends only on Phase 2 completion. No dependency on other stories.
- **US2 (P2)**: Extends US1's session infrastructure — start after T023 (US1 checkpoint).
- **US3 (P3)**: Depends on Phase 2 schema only. Can technically start in parallel with US1/US2 if working on backend schemas alone.
- **US4 (P4)**: Depends on US1 (auth gate) and US3 (admin dependency) being complete.

### Within Each Phase

- Models before services
- Services before endpoints
- Backend before frontend integration
- Tests written alongside implementation

---

## Parallel Opportunities

### Phase 2 (3 parallel streams)

```
Stream A: T007 → T008 (Supabase setup — manual, sequential)
Stream B: T010 + T011 + T012 (config, enums, logger — all independent files)
```

### Phase 3 (US1 — 2 parallel streams after T013)

```
Stream A (Backend):   T013 → T014 → T015 → T024
Stream B (Frontend):  T016 + T017 → T018 → T019 + T020 → T021 → T022 → T023
```

### Phase 5 (US3 — parallel model + dependency work)

```
Stream A: T028 (schemas.py)
Stream B: T029 + T030 (admin dependency + RLS verification)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 (Setup) — ~30 min
2. Complete Phase 2 (Foundational) — ~45 min (includes Supabase manual config)
3. Complete Phase 3 (US1) — ~2 hours
4. **STOP and VALIDATE**: Run all 7 quickstart smoke tests
5. `pytest backend/tests/test_auth.py` — all green

This is a fully working auth layer. Every other feature (VM, AI, Analytics) can now be built on top.

### Incremental Delivery

1. Phase 1 + 2 + 3 → **Working auth MVP** — deploy to Render + Vercel
2. Phase 4 → Session persistence hardened
3. Phase 5 → Data isolation verified
4. Phase 6 → Admin access gated
5. Phase 7 → Production-ready

---

## Notes

- **[P]** tasks touch different files and have no shared state — safe to run in parallel
- **US3 schema tasks** (T028–T030) are also used as input by the VM and AI features — complete these before starting feature 002
- The `contracts/jwt-auth.md` and `contracts/schema.sql` files are consumed by future features — treat them as read-only after this feature is complete
- Commit after each checkpoint (T008, T024, T027, T030, T033, T037)
- Stop at Phase 3 checkpoint for the quickest demo path
