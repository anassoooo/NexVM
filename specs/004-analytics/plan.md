# Implementation Plan: Analytics

**Branch**: `004-analytics` | **Date**: 2026-04-07 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `/specs/004-analytics/spec.md`  
**Depends on**: `003-ai-command-processing` fully complete — `ai_usage` table populated, VM service layer, auth middleware all in place.

---

## Summary

Add read-only analytics to myVMS. Two new backend endpoints query existing tables and return counts. Two existing frontend pages replace placeholder content with live stat cards. No new database tables, no new dependencies.

---

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript 5.x (frontend)  
**New Backend Files**: `services/analytics_service.py`, `routes/analytics.py` (+ update `main.py`, `models/schemas.py`)  
**New Frontend Files**: none (+ update `types/index.ts`, `app/admin/page.tsx`)  
**Existing Reused Files**: `dependencies.py` (`get_current_user`, `get_current_admin_user`), `db.py` (`get_supabase_client`)  
**Storage**: Supabase PostgreSQL — `vms`, `ai_usage`, `profiles` tables (read-only queries)  
**Testing**: pytest + unittest.mock.patch for Supabase client  
**Constraints**: Read-only endpoints; no caching; no time-range filters; no charting libraries

---

## Constitution Check

| Principle / Rule | Requirement | Status | Notes |
|---|---|---|---|
| §II — Auth Before Everything | Analytics endpoints protected by JWT | **PASS** | Uses `Depends(get_current_user)` and `Depends(get_current_admin_user)` |
| §VI.3 — No direct frontend DB writes | Frontend calls backend API | **PASS** | All data fetched from `/api/v1/analytics` |
| §XI.1 — Auth Required | Endpoints require valid JWT | **PASS** | No unauthenticated analytics access |
| §XI.2 — Input Validation | No user input — read-only endpoints | **PASS** | GET endpoints with no request body |
| §XII.1 — Mandatory Logging | Analytics are reads — logging not required | **PASS** | No state changes, no audit log needed |
| §V — YAGNI | No caching, no charts, no time filters | **PASS** | Stat cards with all-time totals only |

**All gates pass. No violations. Proceeding to implementation.**

---

## Project Structure

### Documentation (this feature)

```text
specs/004-analytics/
├── plan.md              ✅ This file
├── spec.md              ✅ Feature specification
├── research.md          ✅ Phase 0 output
├── data-model.md        ✅ Schema and data flow
├── quickstart.md        ✅ Smoke test guide
├── tasks.md             ✅ Task breakdown
├── contracts/
│   └── analytics-api.md ✅ API contract
└── checklists/
    ├── requirements.md  ✅ Spec quality gate
    └── implementation.md ✅ Pre/post implementation gate
```

### Source Code Changes

```text
backend/
├── app/
│   ├── main.py                      MODIFY — include analytics router
│   ├── models/
│   │   └── schemas.py               MODIFY — add UserAnalytics, AdminAnalytics
│   ├── routes/
│   │   └── analytics.py             CREATE — GET / and GET /admin endpoints
│   └── services/
│       └── analytics_service.py     CREATE — get_user_analytics, get_admin_analytics
└── tests/
    └── test_analytics_service.py    CREATE — 8 mocked Supabase test cases

frontend/
├── app/
│   ├── ai/
│   │   └── page.tsx                 MODIFY — auto-call analytics on session start for AI greeting
│   └── admin/
│       └── page.tsx                 MODIFY — replace [placeholder] with system metrics
└── types/
    └── index.ts                     MODIFY — add UserAnalytics, AdminAnalytics interfaces
```

**No database migrations required.**

---

## Complexity Tracking

No constitution violations. All tasks within 4-hour complexity budget (§10.3). Pure read endpoints — no state machines, no external API calls, no async complexity. Frontend changes are server components with inline stat card rendering — no new client components required.
