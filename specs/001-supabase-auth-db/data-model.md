# Data Model: Supabase Auth & Database Setup

**Branch**: `001-supabase-auth-db` | **Date**: 2026-04-04

---

## Entity Overview

```text
auth.users (Supabase-managed)
    │ id: uuid (pk)
    │ email: text (unique)
    │
    │ 1:1
    ▼
profiles
    │ id: uuid (pk, fk → auth.users)
    │ is_admin: boolean
    │ created_at: timestamptz
    │
    │ 1:N
    ├──────────────────────┬──────────────────┐
    ▼                      ▼                  ▼
  vms                    logs            ai_usage
```

---

## Table: auth.users

Managed entirely by Supabase Auth. Not created or modified by migrations.

| Column | Type | Notes |
|---|---|---|
| id | uuid | Primary key — referenced by all application tables |
| email | text | Unique; validated and managed by Supabase Auth |
| (others) | — | Supabase-internal fields; not accessed directly |

**Access**: Read via `auth.uid()` in RLS policies. Never queried directly from application code.

---

## Table: profiles

Extends `auth.users` with application-specific fields. Created automatically on user signup via trigger; created on first login if trigger failed (fallback).

| Column | Type | Default | Nullable | Notes |
|---|---|---|---|---|
| id | uuid | — | NO | PK + FK → auth.users.id (CASCADE DELETE) |
| is_admin | boolean | false | NO | Admin role flag; set manually via SQL for MVP |
| created_at | timestamptz | now() | NO | UTC timestamp |

**Constraints**:
- `id` is both PK and FK (1:1 with auth.users)
- `CASCADE DELETE`: deleting an auth user removes their profile

**RLS**:
- Users can read their own profile: `auth.uid() = id`
- Admins can read all profiles: `profiles.is_admin = true`
- No update policy for MVP (admin flag set via direct SQL)

---

## Table: vms

Tracks all virtual machines registered in the system.

| Column | Type | Default | Nullable | Notes |
|---|---|---|---|---|
| id | uuid | gen_random_uuid() | NO | PK |
| user_id | uuid | — | NO | FK → auth.users.id (CASCADE DELETE) |
| name | text | — | NO | Human-readable VM name; 1–50 characters |
| os | text | — | NO | Operating system label (e.g., "Ubuntu 22.04") |
| ram | int | — | NO | RAM in MB; CHECK: 512 ≤ ram ≤ 16384 |
| status | text | 'stopped' | NO | CHECK: one of stopped/starting/running/stopping/error |
| error_message | text | null | YES | Populated only when status = 'error' |
| created_at | timestamptz | now() | NO | UTC |
| updated_at | timestamptz | now() | NO | UTC; updated on every status change |

**Constraints**:
```sql
CHECK (status IN ('stopped', 'starting', 'running', 'stopping', 'error'))
CHECK (ram >= 512 AND ram <= 16384)
```

**State transitions**:

```text
stopped  → starting  (on start action)
starting → running   (on VBoxManage success)
starting → error     (on VBoxManage failure)
running  → stopping  (on stop action)
stopping → stopped   (on VBoxManage success)
stopping → error     (on VBoxManage failure)
error    → starting  (on retry/start action)
```

**Index**: `CREATE INDEX ON vms (user_id)` — supports per-user VM list queries.

**RLS**:
- Users access own VMs: `auth.uid() = user_id`
- Admins access all VMs: `profiles.is_admin = true`

---

## Table: logs

Append-only audit log. Never updated after insert.

| Column | Type | Default | Nullable | Notes |
|---|---|---|---|---|
| id | uuid | gen_random_uuid() | NO | PK |
| user_id | uuid | — | YES | FK → auth.users.id (SET NULL on delete — preserve audit trail); if non-null, must reference an existing auth.users.id |
| action | text | — | NO | Whitelisted action: create_vm / start_vm / stop_vm / delete_vm / login / ai_command |
| target | text | — | NO | VM UUID string, or literal "ai", or "auth" for login events |
| status | text | — | NO | "success" or "failure" |
| message | text | — | NO | Human-readable detail or error context |
| created_at | timestamptz | now() | NO | UTC |

**Design note**: `user_id` uses `SET NULL ON DELETE` (not CASCADE) so audit records survive user account deletion. This preserves the audit trail for admin review.

**Index**: `CREATE INDEX ON logs (user_id)` — supports per-user log queries.

**RLS**:
- Users read own logs: `auth.uid() = user_id`
- Admins read all logs: `profiles.is_admin = true`

---

## Table: ai_usage

Records every AI command interaction for analytics and abuse detection.

| Column | Type | Default | Nullable | Notes |
|---|---|---|---|---|
| id | uuid | gen_random_uuid() | NO | PK |
| user_id | uuid | — | YES | FK → auth.users.id (SET NULL on delete); if non-null, must reference an existing auth.users.id |
| prompt | text | — | NO | Raw user prompt text |
| response | text | — | NO | Structured JSON response from AI |
| tokens | int | — | NO | Token count for the interaction |
| created_at | timestamptz | now() | NO | UTC |

**Index**: `CREATE INDEX ON ai_usage (user_id)` — supports per-user AI history queries.

**RLS**:
- Users read own AI usage: `auth.uid() = user_id`
- Admins read all AI usage: `profiles.is_admin = true`

---

## Validation Rules Summary

| Entity | Field | Rule | Enforcement |
|---|---|---|---|
| profiles | id | Must match auth.users.id | FK constraint |
| vms | status | One of 5 valid states | CHECK constraint + Pydantic enum |
| vms | ram | 512–16384 MB | CHECK constraint + Pydantic validator |
| vms | name | 1–50 characters | Pydantic validator (not DB constraint) |
| logs | status | "success" or "failure" | Pydantic enum |
| logs | action | Whitelisted actions only | Pydantic enum |
| All tables | user_id | Must reference existing auth user | FK constraint |
