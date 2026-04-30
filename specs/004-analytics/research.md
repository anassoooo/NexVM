# Research: Analytics

**Branch**: `004-analytics` | **Date**: 2026-04-07

---

## 1. Supabase Query Strategy

**Decision**: Use `select("status").eq("user_id", user_id)` for VM queries and count rows by status value in Python. Use `select("id")` for count-only queries.

**Rationale**: The existing codebase uses `.select("*").execute()` and accesses `result.data`. Staying consistent avoids introducing new query patterns. For MVP scale (single-tenant, small VM counts), fetching minimal columns (id or status only) and counting in Python is fast and readable.

**Alternative considered**: `select("*", count="exact")` — supabase-py supports `result.count` with this parameter, which avoids transferring row data. Not used because:
1. Existing codebase never uses it — would be an inconsistency.
2. Status-breakdown requires per-row values anyway (can't just count totals).
3. MVP scale makes the difference negligible.

---

## 2. Admin Authorization

**Decision**: Reuse the existing `get_current_admin_user` dependency from `backend/app/dependencies.py`. No new guard code needed.

**Implementation**: `get_current_admin_user` chains from `get_current_user`, queries `profiles.is_admin`, and raises HTTP 403 if false. The analytics admin endpoint simply uses `Depends(get_current_admin_user)` — identical to the pattern used in other admin-gated routes.

---

## 3. Frontend Fetch Pattern

**Decision**: Fetch analytics in the server component using `session.access_token` — same pattern as `app/vms/page.tsx`.

**Pattern**:
```typescript
const { data: { session } } = await supabase.auth.getSession();
const BASE_URL = process.env.NEXT_PUBLIC_API_URL;
let analytics: UserAnalytics | null = null;
try {
  const res = await fetch(`${BASE_URL}/api/v1/analytics`, {
    headers: { Authorization: `Bearer ${session?.access_token}` },
  });
  if (res.ok) analytics = await res.json();
} catch { /* graceful fallback */ }
```

**Why server component**: Auth check already happens server-side. Fetching analytics in the same server component avoids a client-side loading state and keeps the page simple (no `"use client"` needed).

**Graceful fallback**: If the fetch fails (network error, 500), `analytics` stays `null` and the page renders "—" for each stat. The page does not crash.

---

## 4. No Charting Library

**Decision**: Stat cards only — no charts. No new npm dependency.

**Rationale**: Charting libraries (Chart.js, Recharts, etc.) add bundle size and complexity for metrics that are just a handful of integers. Stat cards (number + label in a styled div) deliver the same value at zero cost. Deferred if a richer analytics view is needed in future.

---

## 5. No Caching

**Decision**: Fresh fetch on every page load. No React Query, no SWR, no server-side cache.

**Rationale**: Single-tenant MVP. The admin page and dashboard are not high-frequency pages. Stale counts would be more confusing than the negligible latency of a fresh Supabase read.
