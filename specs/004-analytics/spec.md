# Feature Specification: Analytics

**Feature Branch**: `004-analytics`  
**Created**: 2026-04-07  
**Status**: Complete  
**Input**: `docs/implementation-plan.md` — "Analytics" vertical slice  
**Depends on**: `003-ai-command-processing` (ai_usage table populated — must be complete)

---

## Overview

This spec adds analytics visibility to myVMS. Regular users see a live summary of their own VMs (status breakdown, AI command count) on their dashboard. Admin users see system-wide metrics (total users, all VMs, all AI commands) on the admin page.

All data comes from existing tables (`vms`, `ai_usage`, `profiles`) — no new database tables or migrations are required. The feature is purely additive: two new read-only API endpoints and two updated frontend pages.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — AI Chat VM Summary (Priority: P1)

A logged-in regular user opens `/ai` and immediately sees an AI-generated greeting summarizing their VM status breakdown, instead of a blank chat.

**Why this priority**: The AI greeting replaces the removed `/dashboard` stat cards as the primary at-a-glance view. This is the first thing users see after login.

**Independent Test**: Can be tested by creating a few VMs with different statuses, reloading `/ai`, and verifying the AI's opening message contains the correct counts.

**Acceptance Scenarios**:

1. **Given** a user with 3 VMs (1 running, 1 stopped, 1 error), **When** they load `/ai`, **Then** the AI's opening message includes Total: 3, Running: 1, Stopped: 1, Errors: 1.
2. **Given** a user with no VMs, **When** they load `/ai`, **Then** the AI's opening message shows Total: 0 (not an error or blank greeting).
3. **Given** a user who has sent 5 AI commands, **When** they load `/ai`, **Then** the AI greeting does NOT include the AI command count — that is on-demand only.
4. **Given** the analytics API is unavailable, **When** the user loads `/ai`, **Then** the AI greeting falls back to a generic welcome message — no crash.

---

### User Story 2 — Admin System Metrics (Priority: P1)

An admin user visits `/admin` and sees system-wide metrics instead of the `[placeholder]` text.

**Why this priority**: The admin page exists and has the correct auth guard but has never had real content. This completes the feature.

**Independent Test**: Can be tested by logging in as an admin, visiting `/admin`, and verifying counts match Supabase table row counts.

**Acceptance Scenarios**:

1. **Given** an admin with 2 users, 5 total VMs (2 running, 2 stopped, 1 error), and 10 AI commands, **When** they visit `/admin`, **Then** they see Total Users: 2, Total VMs: 5, Running: 2, Stopped: 2, Errors: 1, AI Commands: 10.
2. **Given** a non-admin user, **When** they navigate to `/admin`, **Then** they are redirected to `/ai` (existing guard — unchanged).
3. **Given** a non-admin user calls `GET /api/v1/analytics/admin` directly, **Then** they receive HTTP 403 — Admin access required.

---

### Edge Cases

- **No data**: All counts gracefully return 0 — no division by zero, no null errors.
- **Admin sees all users' VMs**: Admin analytics are not filtered by user_id — they aggregate across all users.
- **User analytics are scoped**: User analytics are filtered to the caller's user_id — users cannot see each other's counts.
- **Unauthenticated API call**: Both endpoints require JWT — return 401/403 on missing or invalid token.
- **AI assistant analytics failure**: If `GET /api/v1/analytics` fails during an AI conversation, the assistant MUST acknowledge the failure gracefully in natural language rather than returning raw error data.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST expose `GET /api/v1/analytics` returning VM status counts and AI command count scoped to the authenticated user.
- **FR-002**: System MUST expose `GET /api/v1/analytics/admin` returning system-wide VM counts, total users, and total AI commands — accessible to admin users only.
- **FR-003**: `GET /api/v1/analytics/admin` MUST return HTTP 403 for non-admin authenticated users.
- **FR-004**: Both endpoints MUST require authentication — unauthenticated requests return HTTP 401/403.
- **FR-005**: **REMOVED** — Regular users interact exclusively through the AI chat interface (`/ai`). The `/dashboard` page and its stat cards no longer exist for regular users. Analytics are surfaced via the AI assistant only (see FR-009).
- **FR-006**: The `/admin` page MUST display system-wide metrics (total users, total VMs, running/stopped/error breakdown, total AI commands) fetched from `GET /api/v1/analytics/admin`.
- **FR-007**: The `/admin` page MUST degrade gracefully on API failure — display dashes rather than crashing. The AI greeting on `/ai` MUST fall back to a generic welcome message when the analytics API is unreachable.
- **FR-008**: Analytics data MUST be read-only — no writes or mutations via analytics endpoints.
- **FR-009**: The AI assistant MUST call the appropriate analytics endpoint based on the authenticated user's role and incorporate the result into conversational responses. Two trigger modes:
  1. **Session start (proactive)**: The AI MUST open with a brief VM summary every time the chat component mounts (i.e., on every page load) — this replaces the removed dashboard stat cards. No cross-reload deduplication is required. The greeting MUST include: total VM count, running count, stopped count, and error count. AI command count is excluded from the greeting (on-demand only).
  2. **On-demand**: When the user explicitly asks (e.g., "How many VMs do I have running?", "How many total users are there?").
  
  Endpoint selection by role:
  - **Regular user** → `GET /api/v1/analytics` (user-scoped counts).
  - **Admin user** → `GET /api/v1/analytics` for personal VM questions; `GET /api/v1/analytics/admin` for system-wide questions (e.g., "how many total users?", "how many VMs across all users?").
  
  All analytics responses MUST be in the same language the user typed in — no language restriction.

### Key Entities

- **User Analytics**: A snapshot of the authenticated user's VM status counts and total AI command count. Computed on-the-fly from the `vms` and `ai_usage` tables.
- **Admin Analytics**: A system-wide snapshot of all users' VM counts (by status), total user count, and total AI command count. Computed on-the-fly from `vms`, `profiles`, and `ai_usage` tables.

---

## Success Criteria *(mandatory)*

- **SC-001**: A user with N VMs of mixed statuses starts a new AI chat session; the AI's opening message contains correct total, running, stopped, and error counts matching the database — AI command count is absent from the greeting. Validates FR-009 proactive greeting (replaces removed dashboard stat cards).
- **SC-002**: An admin visits `/admin` and sees correct system-wide counts matching the database.
- **SC-003**: `GET /api/v1/analytics/admin` returns HTTP 403 for a non-admin authenticated user — 0 unauthorized accesses.
- **SC-004**: `pytest backend/tests/test_analytics_service.py` passes all 8 test cases.
- **SC-005**: `pytest -q` passes all tests with no regressions — 0 broken prior tests.
- **SC-006**: The `/admin` page shows "—" (not crash/500) when the analytics API is unreachable; the AI greeting on `/ai` falls back to a generic welcome message.
- **SC-007**: `tsc --noEmit` reports no TypeScript errors after adding analytics types.

---

## Assumptions

- The `vms`, `ai_usage`, and `profiles` tables exist and are populated (created in spec 001, used in specs 002–003).
- `get_current_admin_user` dependency already exists in `backend/app/dependencies.py` — no new guard code required.
- The `/admin` page already has a correct auth + admin guard — only the content (placeholder) needs replacing.
- Regular users do not have a `/dashboard` page — analytics are surfaced exclusively via the AI chat greeting (FR-009) and on-demand AI queries. The `/dashboard` route is removed for regular users.
- VM counts are computed by filtering `status` values in Python — no SQL aggregation needed for MVP scale.
- No caching — analytics are fetched fresh on every page load. Acceptable for single-tenant MVP.
- No time-range filtering — totals are all-time counts. MVP scope only.
- The Groq model used for all AI assistant tool-call operations (including analytics queries) is **`llama-4-scout`**. It covers function calling, multilingual input, and text generation — replacing the previously noted `llama3-groq-70b-8192-tool-use-preview`.
- The AI assistant responds in the user's input language — no language restriction is applied to analytics or any other response.

---

## Clarifications

### Session 2026-04-07

- Q: Should analytics include log counts or just VM/AI counts? → A: VM status counts + AI command count only. Log counts are admin-internal detail, deferred.
- Q: Should the dashboard show a chart or just numbers? → A: Numbers only (stat cards). No charting library for MVP — YAGNI.
- Q: Should analytics be cached? → A: No. Fresh on every load for MVP.
- Q: Should there be a time-range filter (last 7 days, etc.)? → A: No. All-time totals only for MVP.

### Session 2026-04-07 (continued)

- Q: Should the AI assistant be able to answer analytics queries conversationally (e.g., "How many VMs do I have running?")? → A: Yes — AI assistant can call the analytics API and include counts in its response (FR-009 added).
- Q: Should the static dashboard analytics stat cards (/dashboard) still exist alongside AI assistant analytics? → A: ~~Keep both~~ **REVISED**: Regular users have AI-only interface — dashboard stat cards removed (FR-005 superseded). Admin analytics page (/admin) stays (FR-006 unchanged).
- Q: Should AI assistant analytics responses match the user's input language? → A: Yes — AI assistant responds in whatever language the user typed in (FR-009 updated; no language restriction).
- Q: Should the AI assistant proactively surface analytics, or only respond when explicitly asked? → A: ~~On-demand only~~ **REVISED**: Proactive on session start (brief VM summary greeting replaces removed dashboard); on-demand for all subsequent queries (FR-009 updated).
- Q: Which Groq model should the AI assistant use for analytics (and all tool-call operations)? → A: ~~`llama3-groq-70b-8192-tool-use-preview`~~ **REVISED**: `llama-4-scout` — covers function calling, multilingual, and text generation per current Groq catalog. Applied across specs 003 and 004.

### Session 2026-04-08

- Q: For regular users, should the entire app be a single AI chat interface with no dashboard/VM pages? → A: Yes — regular users see only an AI chat interface; all VM operations and analytics happen through it (FR-005 superseded; specs 002 and 004 user-facing pages to be removed).
- Q: What does the admin interface look like? → A: Traditional admin panel — tables, metrics page, structured UI for system oversight (FR-006 and /admin page unchanged).
- Q: Does the login/signup page stay as a traditional form? → A: Yes — traditional login/signup form stays; auth is pre-AI and separate from the chat interface (spec 001 auth pages unchanged).
- Q: What does the AI chat interface look like structurally after login? → A: Full-screen chat — entire viewport is the AI chat after login, no persistent sidebar or panels.
- Q: Should the AI greet with a VM summary on session start given there is no dashboard? → A: Yes — AI opens every session with a brief VM summary (replaces dashboard at-a-glance); on-demand for all subsequent queries (FR-009 revised).

### Session 2026-04-14

- Q: SC-001 referenced `/dashboard` stat cards which were removed by FR-005 (superseded) — should SC-001 be rewritten to test the proactive AI greeting instead? → A: Yes — SC-001 rewritten to validate that the AI's opening message on session start contains correct VM counts matching the database (aligns with FR-009).
- Q: What event defines a "new session" for the FR-009 proactive greeting — login, page load, or tab session? → A: Page load (component mount) — greeting fires every time the chat component mounts; no cross-reload deduplication required (FR-009 updated).
- Q: Which fields must the proactive AI greeting include — total+breakdown only, or also AI command count? → A: Total VM count + status breakdown (running, stopped, errors) only; AI command count excluded from greeting, available on-demand (FR-009 and SC-001 updated).
