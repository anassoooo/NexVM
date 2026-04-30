# Tasks: Supabase Auth & Database Setup

**Input**: Design documents from `/specs/001-supabase-auth-db/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Backend auth tests included (`backend/tests/test_auth.py`) — covers JWT validation, expiry, and missing-token scenarios per spec requirements.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `backend/`, `frontend/`, `supabase/migrations/`
- Backend source: `backend/app/`, tests: `backend/tests/`
- Frontend source: `frontend/app/`, `frontend/lib/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization, directory structure, and dependency scaffolding.

- [ ] T001 Create backend directory structure — `backend/app/routes/`, `backend/app/models/`, `backend/app/utils/`, `backend/tests/` with `__init__.py` files
- [ ] T002 Initialize Next.js 14 project in `frontend/` — `npx create-next-app@14` with TypeScript, Tailwind, App Router
- [ ] T003 Create `supabase/migrations/` directory at repo root
- [ ] T004 [P] Create `backend/requirements.txt` with dependencies: fastapi, uvicorn[standard], supabase, python-jose[cryptography], pydantic-settings, httpx, groq, pytest, pytest-asyncio
- [ ] T005 [P] Create `backend/.env.example` — SUPABASE_URL, SUPABASE_KEY, SUPABASE_SERVICE_KEY, SUPABASE_JWT_SECRET, GROQ_API_KEY, FRONTEND_URL, VBOXMANAGE_PATH
- [ ] T006 [P] Create `frontend/.env.example` — NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY, NEXT_PUBLIC_API_URL

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Database schema, Supabase configuration, and backend config/enums. All user stories depend on this phase.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T007 Copy `specs/001-supabase-auth-db/contracts/schema.sql` to `supabase/migrations/001_initial_schema.sql` — canonical migration with is_admin() helper, profiles/vms/logs/ai_usage tables, constraints, indexes, RLS policies, and auto-profile trigger
- [ ] T008 Run `001_initial_schema.sql` in Supabase SQL Editor and verify: tables `profiles`, `vms`, `logs`, `ai_usage` exist with RLS enabled; trigger `on_auth_user_created` listed under Database → Triggers
- [ ] T009 Configure Supabase Auth settings in dashboard — JWT expiry = 86400s; min password length = 8; password must contain a number; rate limit email sign-in = 10 per 900 seconds (FR-016, FR-017)
- [ ] T010 [P] Create `backend/app/config.py` — `Settings` class via pydantic-settings loading SUPABASE_URL, SUPABASE_KEY, SUPABASE_SERVICE_KEY, SUPABASE_JWT_SECRET, GROQ_API_KEY, FRONTEND_URL, VBOXMANAGE_PATH from env
- [ ] T011 [P] Create `backend/app/models/enums.py` — `VMStatus` (stopped/starting/running/stopping/error), `LogStatus` (success/failure), `LogAction` (create_vm/start_vm/stop_vm/delete_vm/login/ai_command)
- [ ] T012 [P] Create `backend/app/utils/logger.py` — structured JSON logger with fields: user_id, action, target, status, message, timestamp (UTC ISO 8601)

**Checkpoint**: Schema live in Supabase, auth settings configured, backend config + enums ready. `SELECT * FROM profiles;` returns empty table with correct columns.

---

## Phase 3: User Story 1 — Register and Access the System (Priority: P1) 🎯 MVP

**Goal**: User can sign up, get auto-redirected to `/ai` (regular) or `/admin` (admin), and their profile is auto-created. Login, logout, and unauthenticated redirect all work.

**Independent Test**: Create account → `/ai` loads → `profiles` table has row → logout → redirect to `/login` → navigate to `/ai` → redirect to `/login`.

### Backend

- [ ] T013 [US1] Implement `get_current_user` dependency in `backend/app/dependencies.py` — decode HS256 JWT via python-jose, validate aud="authenticated" + sub + exp + iss + role claims, call `ensure_profile_exists(user_id)` fallback, return user UUID string, raise HTTPException(401) on any failure
- [ ] T014 [P] [US1] Implement `ensure_profile_exists(user_id)` helper in `backend/app/dependencies.py` — query profiles by id, insert {id, is_admin: false} if missing (idempotent, per contracts/jwt-auth.md)
- [ ] T015 [P] [US1] Create `backend/app/routes/health.py` — `GET /api/v1/health` returns `{"status": "ok", "vboxmanage": "<version or error>"}`, no auth required, runs VBoxManage --version with 5s timeout
- [ ] T016 [US1] Create `backend/app/main.py` — FastAPI app with CORSMiddleware (FRONTEND_URL origin only, GET/POST methods), lifespan handler for Supabase client init, include health router under `/api/v1`

### Frontend

- [ ] T017 [P] [US1] Create `frontend/lib/supabase/client.ts` — export createBrowserClient using @supabase/ssr with NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY
- [ ] T018 [P] [US1] Create `frontend/lib/supabase/server.ts` — export createServerClient factory using cookies() from next/headers, for Server Components and Route Handlers
- [ ] T019 [US1] Create `frontend/middleware.ts` — use createServerClient to read session; if no session and route is not under /(auth), redirect to /login; config.matcher excludes _next/static, _next/image, favicon.ico
- [ ] T020 [P] [US1] Create `frontend/app/(auth)/signup/page.tsx` — email/password form, client-side validation (≥8 chars + ≥1 number per FR-017), Supabase signUp, check profiles.is_admin for redirect to /admin or /ai
- [ ] T021 [P] [US1] Create `frontend/app/(auth)/login/page.tsx` — email/password form, Supabase signInWithPassword, role-aware redirect (/admin or /ai), display error message including rate-limit 429 with retry time
- [ ] T022 [US1] Create `frontend/app/layout.tsx` — root layout with Tailwind CSS globals, dark green theme, metadata, font setup
- [ ] T023 [US1] Create `frontend/app/page.tsx` — server component, check session via createServerClient, query profiles.is_admin, redirect to /admin (admin) or /ai (regular) if authenticated, /login if not
- [ ] T024 [US1] Create `frontend/app/(auth)/ai/page.tsx` — protected server component, render "AI Chat" placeholder with user email, include logout button calling supabase.auth.signOut() → redirect to /login

### Backend Tests

- [ ] T025 [US1] Create `backend/tests/test_auth.py` — three pytest cases with httpx.AsyncClient: (1) valid unexpired JWT → 200 from protected endpoint, (2) expired JWT → 401, (3) missing Authorization header → 401. Generate test JWTs with python-jose using SUPABASE_JWT_SECRET.

**Checkpoint**: Registration, login, logout, and redirect all work end-to-end. Profile row appears after signup. `pytest backend/tests/test_auth.py` passes all three cases.

---

## Phase 4: User Story 2 — Session Persistence Across Page Reloads (Priority: P2)

**Goal**: Logged-in user closes browser, returns within 24h — still authenticated. After 24h, redirected to /login with clear message. Logout is per-device only.

**Independent Test**: Login as regular user → close browser → reopen → navigate to /ai → still logged in. For admin user → lands on /admin.

- [ ] T026 [US2] Update `frontend/middleware.ts` — handle expired/invalid session: when getSession returns null after previously valid cookie, clear stale cookie and redirect to `/login?reason=session_expired`
- [ ] T027 [P] [US2] Create `frontend/hooks/use-auth.ts` — client hook wrapping supabase.auth.getSession() and onAuthStateChange(), returns { session, user, loading }
- [ ] T028 [US2] Update `frontend/app/(auth)/login/page.tsx` — read `?reason=session_expired` query param, display "Your session has expired. Please log in again." above the form when present

**Checkpoint**: Close browser, reopen within session window → still logged in. Manually expire cookie → redirected to /login with "session expired" message.

---

## Phase 5: User Story 3 — Data Isolation Between Users (Priority: P3)

**Goal**: Each user sees only their own VMs, logs, and AI usage. Admin sees all records. Enforced at the database layer via RLS.

**Independent Test**: Create two accounts (A, B), insert VM records via SQL, login as A → only A's VMs returned; login as B → only B's VMs.

- [ ] T029 [P] [US3] Create `backend/app/models/schemas.py` — Pydantic models: VMCreate (name 1-50, os, ram 512-16384), VMResponse (all VM fields), LogResponse, AIUsageResponse, UserProfile (id, is_admin)
- [ ] T030 [US3] Add `get_current_admin_user` dependency to `backend/app/dependencies.py` — calls get_current_user, queries profiles.is_admin, raises HTTPException(403, "Admin access required") if not admin
- [ ] T031 [US3] Verify RLS isolation manually — run test queries from data-model.md in Supabase SQL Editor: confirm user policy blocks cross-user access and admin policy allows full access across all tables

**Checkpoint**: Two accounts created, user A querying user B's data returns empty. Admin account queries all records successfully.

---

## Phase 6: User Story 4 — Admin Role Recognition (Priority: P4)

**Goal**: User with `is_admin = true` accesses `/admin`. Regular user accessing `/admin` is silently redirected to `/ai` (no 403 error page).

**Independent Test**: Set `is_admin = true` on a profile → login → `/admin` loads. Login as regular user → `/admin` redirects to `/ai`.

- [ ] T032 [US4] Update `frontend/middleware.ts` — add admin check for `/admin` routes: query profiles.is_admin via createServerClient, silently redirect non-admin users to /ai (per spec edge case — no error page)
- [ ] T033 [P] [US4] Create `frontend/app/admin/page.tsx` — admin-only server component, verify is_admin, render admin panel placeholder with user email, include links to /admin/vms and /ai
- [ ] T034 [P] [US4] Create `frontend/app/admin/vms/page.tsx` — admin-only server component, verify is_admin, render "All VMs" placeholder, redirect non-admin to /ai

**Checkpoint**: Admin user reaches /admin. Regular user accessing /admin silently redirected to /ai.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Deployment readiness, shared utilities, and final validation.

- [ ] T035 [P] Create `backend/Dockerfile` — FROM python:3.12-slim, copy requirements.txt, pip install, copy app/, EXPOSE 8000, CMD uvicorn app.main:app --host 0.0.0.0 --port 8000
- [ ] T036 [P] Create `frontend/types/index.ts` — TypeScript types matching schemas.py: VM, Log, AIUsage, UserProfile
- [ ] T037 [P] Create `frontend/lib/api.ts` — base API wrapper, inject Authorization: Bearer <token> via supabase.auth.getSession(), base URL from NEXT_PUBLIC_API_URL, typed error handling extracting detail from responses
- [ ] T038 Run every step in `specs/001-supabase-auth-db/quickstart.md` and verify all smoke tests pass. Fix any gaps found.

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

- **US1 (P1)**: Depends only on Phase 2. No dependency on other stories.
- **US2 (P2)**: Extends US1's session infrastructure — start after US1 checkpoint.
- **US3 (P3)**: Depends on Phase 2 schema only. Can start in parallel with US1/US2 for backend schema work.
- **US4 (P4)**: Depends on US1 (auth gate) and US3 (admin dependency) being complete.

### Within Each Phase

- Models before services
- Services before endpoints
- Backend before frontend integration
- Tests written alongside implementation

---

## Parallel Opportunities

### Phase 2 (2 parallel streams)

```text
Stream A: T007 → T008 → T009 (Supabase setup — manual, sequential)
Stream B: T010 + T011 + T012 (config, enums, logger — all independent files)
```

### Phase 3 / US1 (2 parallel streams after T013)

```text
Stream A (Backend):   T013 + T014 → T015 → T016 → T025
Stream B (Frontend):  T017 + T018 → T019 → T020 + T021 → T022 → T023 → T024
```

### Phase 5 / US3 (parallel model + dependency work)

```text
Stream A: T029 (schemas.py)
Stream B: T030 + T031 (admin dependency + RLS verification)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 (Setup) — ~30 min
2. Complete Phase 2 (Foundational) — ~45 min (includes Supabase manual config)
3. Complete Phase 3 (US1) — ~2 hours
4. **STOP and VALIDATE**: Run quickstart smoke tests
5. `pytest backend/tests/test_auth.py` — all green

This is a fully working auth layer. Every other feature (VM, AI, Analytics) builds on top.

### Incremental Delivery

1. Phase 1 + 2 + 3 → **Working auth MVP** — deploy to Render + Vercel
2. Phase 4 → Session persistence hardened
3. Phase 5 → Data isolation verified
4. Phase 6 → Admin access gated
5. Phase 7 → Production-ready

---

## Notes

- **[P]** tasks touch different files with no shared state — safe to run in parallel
- **US3 schemas** (T029) are also consumed by VM and AI features — complete before starting feature 002
- `contracts/jwt-auth.md` and `contracts/schema.sql` are read-only after this feature — future features depend on them
- Commit after each checkpoint (T012, T025, T028, T031, T034, T038)
- Regular users redirect to `/ai` (NOT /dashboard) — admin users redirect to `/admin`
- Non-admin accessing `/admin/*` is a silent redirect to `/ai` — never a 403 error page
