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

### User Story 1 — Dashboard VM Summary (Priority: P1)

A logged-in user visits `/dashboard` and immediately sees how many VMs they have and their status breakdown, instead of a filler placeholder.

**Why this priority**: The dashboard is the first page users land on. Replacing filler text with real data is the primary deliverable of this spec.

**Independent Test**: Can be tested by creating a few VMs with different statuses, visiting the dashboard, and verifying the counts match.

**Acceptance Scenarios**:

1. **Given** a user with 3 VMs (1 running, 1 stopped, 1 error), **When** they visit `/dashboard`, **Then** the dashboard shows Total: 3, Running: 1, Stopped: 1, Errors: 1.
2. **Given** a user with no VMs, **When** they visit `/dashboard`, **Then** all counts show 0 (not blank or error).
3. **Given** a user who has sent 5 AI commands, **When** they visit `/dashboard`, **Then** "AI Commands" shows 5.
4. **Given** the analytics API is unavailable, **When** the user visits `/dashboard`, **Then** stat values show "—" (dash) and the page does not crash.

---

### User Story 2 — Admin System Metrics (Priority: P1)

An admin user visits `/admin` and sees system-wide metrics instead of the `[placeholder]` text.

**Why this priority**: The admin page exists and has the correct auth guard but has never had real content. This completes the feature.

**Independent Test**: Can be tested by logging in as an admin, visiting `/admin`, and verifying counts match Supabase table row counts.

**Acceptance Scenarios**:

1. **Given** an admin with 2 users, 5 total VMs (2 running, 2 stopped, 1 error), and 10 AI commands, **When** they visit `/admin`, **Then** they see Total Users: 2, Total VMs: 5, Running: 2, Stopped: 2, Errors: 1, AI Commands: 10.
2. **Given** a non-admin user, **When** they navigate to `/admin`, **Then** they are redirected to `/dashboard` (existing guard — unchanged).
3. **Given** a non-admin user calls `GET /api/v1/analytics/admin` directly, **Then** they receive HTTP 403 — Admin access required.

---

### Edge Cases

- **No data**: All counts gracefully return 0 — no division by zero, no null errors.
- **Admin sees all users' VMs**: Admin analytics are not filtered by user_id — they aggregate across all users.
- **User analytics are scoped**: User analytics are filtered to the caller's user_id — users cannot see each other's counts.
- **Unauthenticated API call**: Both endpoints require JWT — return 401/403 on missing or invalid token.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST expose `GET /api/v1/analytics` returning VM status counts and AI command count scoped to the authenticated user.
- **FR-002**: System MUST expose `GET /api/v1/analytics/admin` returning system-wide VM counts, total users, and total AI commands — accessible to admin users only.
- **FR-003**: `GET /api/v1/analytics/admin` MUST return HTTP 403 for non-admin authenticated users.
- **FR-004**: Both endpoints MUST require authentication — unauthenticated requests return HTTP 401/403.
- **FR-005**: The `/dashboard` page MUST display the user's VM status counts (total, running, stopped, error) and AI command count fetched from `GET /api/v1/analytics`.
- **FR-006**: The `/admin` page MUST display system-wide metrics (total users, total VMs, running/stopped/error breakdown, total AI commands) fetched from `GET /api/v1/analytics/admin`.
- **FR-007**: Both frontend pages MUST degrade gracefully on API failure — display dashes rather than crashing.
- **FR-008**: Analytics data MUST be read-only — no writes or mutations via analytics endpoints.

### Key Entities

- **User Analytics**: A snapshot of the authenticated user's VM status counts and total AI command count. Computed on-the-fly from the `vms` and `ai_usage` tables.
- **Admin Analytics**: A system-wide snapshot of all users' VM counts (by status), total user count, and total AI command count. Computed on-the-fly from `vms`, `profiles`, and `ai_usage` tables.

---

## Success Criteria *(mandatory)*

- **SC-001**: A user with N VMs of mixed statuses visits `/dashboard` and sees correct counts matching the database.
- **SC-002**: An admin visits `/admin` and sees correct system-wide counts matching the database.
- **SC-003**: `GET /api/v1/analytics/admin` returns HTTP 403 for a non-admin authenticated user — 0 unauthorized accesses.
- **SC-004**: `pytest backend/tests/test_analytics_service.py` passes all 8 test cases.
- **SC-005**: `pytest -q` passes all tests with no regressions — 0 broken prior tests.
- **SC-006**: Both pages show "—" (not crash/500) when the analytics API is unreachable.
- **SC-007**: `tsc --noEmit` reports no TypeScript errors after adding analytics types.

---

## Assumptions

- The `vms`, `ai_usage`, and `profiles` tables exist and are populated (created in spec 001, used in specs 002–003).
- `get_current_admin_user` dependency already exists in `backend/app/dependencies.py` — no new guard code required.
- The `/admin` page already has a correct auth + admin guard — only the content (placeholder) needs replacing.
- The `/dashboard` page already has auth — only the filler text needs replacing with fetched data.
- VM counts are computed by filtering `status` values in Python — no SQL aggregation needed for MVP scale.
- No caching — analytics are fetched fresh on every page load. Acceptable for single-tenant MVP.
- No time-range filtering — totals are all-time counts. MVP scope only.

---

## Clarifications

### Session 2026-04-07

- Q: Should analytics include log counts or just VM/AI counts? → A: VM status counts + AI command count only. Log counts are admin-internal detail, deferred.
- Q: Should the dashboard show a chart or just numbers? → A: Numbers only (stat cards). No charting library for MVP — YAGNI.
- Q: Should analytics be cached? → A: No. Fresh on every load for MVP.
- Q: Should there be a time-range filter (last 7 days, etc.)? → A: No. All-time totals only for MVP.
