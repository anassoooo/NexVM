# Implementation Plan: Supabase Auth & Database Setup

**Branch**: `001-supabase-auth-db` | **Date**: 2026-04-04 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `/specs/001-supabase-auth-db/spec.md`

---

## Summary

Establish the identity and persistence foundation for myVMS. This plan covers: Supabase project configuration (auth settings, JWT expiry, password policy, rate limiting), PostgreSQL schema migration (profiles, vms, logs, ai_usage), Row Level Security policies, auto-profile trigger with login-time fallback, and the FastAPI JWT validation dependency that all other backend features will reuse.

---

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript 5.x (frontend)  
**Primary Dependencies**: FastAPI, supabase-py, pydantic-settings, python-jose[cryptography], uvicorn; @supabase/ssr, @supabase/supabase-js, Next.js 14  
**Storage**: Supabase PostgreSQL (hosted), cookie-based session storage (frontend)  
**Testing**: pytest + pytest-asyncio (backend unit/integration); manual smoke tests (frontend, MVP)  
**Target Platform**: Render (backend Docker container), Vercel (frontend), Supabase cloud (DB + auth)  
**Project Type**: Fullstack web service (REST backend + SSR frontend)  
**Performance Goals**: Registration complete in < 60s end-to-end (SC-001); auth middleware adds < 100ms per request  
**Constraints**: 24-hour session expiry; lockout after 10 failed attempts/15 min; min 8-char password with ≥1 number; single-tenant MVP  
**Scale/Scope**: One VirtualBox host, one user or small team; no horizontal scaling required for MVP

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle / Rule | Requirement | Status | Notes |
|---|---|---|---|
| §II — Auth Before Everything | Every endpoint protected by Supabase JWT | **PASS** | This feature defines the JWT validation dependency used by all routes |
| §II — Admin routes check admin claim | Admin routes verify `is_admin` in profiles | **PASS** | RLS policy + backend dependency enforce this |
| §VI.1 — Schema Consistency | Four canonical tables: users, vms, logs, ai_usage | **PASS** | All four defined in migration; `users` managed by Supabase auth |
| §VI.2 — Referential Integrity | All relations via explicit foreign keys | **PASS** | `profiles.id → auth.users`, `vms.user_id → auth.users`, `logs.user_id → auth.users`, `ai_usage.user_id → auth.users` |
| §VI.3 — No direct frontend DB writes | Frontend must not write to DB (auth excepted) | **PASS** | Frontend uses Supabase auth SDK for login/signup only; all other writes go via backend API |
| §XI.1 — Auth Required | All endpoints require valid JWT | **PASS** | `GET /api/v1/health` is the only unauthenticated endpoint (explicitly justified: liveness probe) |
| §XI.2 — Input Validation | Validate at API boundary | **PASS** | Pydantic models validate all request bodies; JWT claims validated before business logic |
| §XII.1 — Mandatory Logging | Auth events logged before response | **PASS** | Login events written to `logs` table (FR-011); happens before response per §12.1 rule |
| §V — YAGNI | No speculative features | **PASS** | Only MVP auth + schema; social logins and admin UI explicitly deferred |

**All gates pass. No violations. Proceeding to Phase 0.**

---

## Project Structure

### Documentation (this feature)

```text
specs/001-supabase-auth-db/
├── plan.md              ✅ This file
├── research.md          ✅ Phase 0 output
├── data-model.md        ✅ Phase 1 output
├── quickstart.md        ✅ Phase 1 output
├── contracts/
│   ├── jwt-auth.md      ✅ Phase 1 output
│   └── schema.sql       ✅ Phase 1 output
└── tasks.md             — Phase 2 output (/speckit-tasks — not created here)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app entry, CORS, lifespan
│   ├── config.py            # Settings via pydantic-settings
│   ├── dependencies.py      # get_current_user() — JWT validation + profile fallback
│   ├── routes/
│   │   └── health.py        # GET /api/v1/health (unauthenticated liveness probe)
│   ├── models/
│   │   ├── schemas.py       # Pydantic models: UserProfile, etc.
│   │   └── enums.py         # VMStatus enum (defined here, used by VM feature)
│   └── utils/
│       └── logger.py        # Structured logging helper
├── tests/
│   └── test_auth.py         # Valid JWT passes, expired JWT rejected, missing JWT rejected
├── requirements.txt
├── Dockerfile
└── .env.example

frontend/
├── app/
│   ├── layout.tsx
│   ├── page.tsx             # Redirect: / → /dashboard (auth) or /login (unauth)
│   ├── (auth)/
│   │   ├── login/page.tsx
│   │   └── signup/page.tsx
│   └── dashboard/
│       └── page.tsx         # Placeholder — first protected page
├── lib/
│   └── supabase/
│       ├── client.ts        # createBrowserClient (browser-side)
│       └── server.ts        # createServerClient (server components + actions)
├── middleware.ts             # Auth gate — redirects unauthenticated users
├── .env.example
└── package.json

supabase/
└── migrations/
    └── 001_initial_schema.sql   # All table creation, RLS, triggers, indexes
```

**Structure Decision**: Web application (Option 2) — separate `backend/` and `frontend/` directories matching the implementation plan. A `supabase/migrations/` directory holds canonical SQL as the single source of truth for schema changes.

---

## Complexity Tracking

No constitution violations to justify. All tasks within 4-hour complexity budget (§10.3).
