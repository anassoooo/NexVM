# Data Model: VM Management

**Branch**: `002-vm-management` | **Date**: 2026-04-06

---

## Overview

This feature introduces **no new database tables**. All persistence uses the `vms` and `logs` tables created in `supabase/migrations/001_initial_schema.sql`. This document describes the service-layer view of those tables — what fields are read and written by each operation, the state machine, and the Pydantic schemas.

---

## Table: vms (from spec 001 — read-only contract)

| Column        | Type        | Default             | Nullable | Notes                                              |
|---------------|-------------|---------------------|----------|----------------------------------------------------|
| id            | uuid        | gen_random_uuid()   | NO       | PK                                                 |
| user_id       | uuid        | —                   | NO       | FK → auth.users.id (CASCADE DELETE)                |
| name          | text        | —                   | NO       | 1–50 chars, alphanumeric + hyphens + spaces        |
| os            | text        | —                   | NO       | Free-text OS label                                 |
| ram           | integer     | —                   | NO       | MB; CHECK 512–16384                                |
| status        | text        | 'stopped'           | NO       | CHECK: stopped/starting/running/stopping/error     |
| error_message | text        | null                | YES      | Populated when status = 'error'; cleared on retry  |
| created_at    | timestamptz | now()               | NO       | UTC                                                |
| updated_at    | timestamptz | now()               | NO       | UTC; updated on every status change                |

**RLS**: Users access only rows where `auth.uid() = user_id`. Admins access all rows. The backend uses the Supabase **service role key** for writes (status updates, inserts, deletes) to bypass RLS — the `user_id` filter is enforced at the application layer via `get_vm_or_404`.

---

## Table: logs (from spec 001 — read-only contract)

Every VM operation writes one row. Written using the service role client. The `action` column is constrained to the whitelisted set defined in spec 001.

| Column     | Written value for VM operations               |
|------------|-----------------------------------------------|
| user_id    | From `get_current_user()` dependency          |
| action     | `create_vm`, `start_vm`, `stop_vm`, `delete_vm` |
| target     | VM UUID string (or `"create_vm"` on creation failure before DB record exists) |
| status     | `"success"` or `"failure"`                    |
| message    | Human-readable detail or VBoxManage stderr    |

---

## VM State Machine

```
                   ┌──────────┐
       ┌──────────>│ stopped  │<───────────┐
       │           └────┬─────┘            │
       │                │ start            │
       │                ▼                  │
       │          ┌──────────┐             │
       │          │ starting │──fail──────>│
       │          └────┬─────┘             │
       │               │ success           │  ┌──────────┐
       │               ▼                   ├──│  error   │
       │          ┌──────────┐             │  └──────────┘
       │  stop    │ running  │             │       │
       │  ┌───────┤          │             │       │ start (retry)
       │  │       └──────────┘             │       │
       │  ▼                                │       ▼
       │ ┌──────────┐                      │  ┌──────────┐
       └─│ stopping │──fail───────────────>│  │ starting │
         └──────────┘                      └──┴──────────┘
```

### Valid Transitions

| From      | Action | To (success) | To (failure) | Rejected if in       |
|-----------|--------|--------------|--------------|----------------------|
| stopped   | start  | running      | error        | starting, stopping   |
| error     | start  | running      | error        | starting, stopping   |
| running   | stop   | stopped      | error        | starting, stopping   |
| stopped   | delete | (removed)    | (no change)  | running, starting, stopping, error |

### State Enforcement Rules

1. **Pre-update before subprocess**: Status is set to "starting" or "stopping" in the DB before calling VBoxManage.
2. **Post-update after subprocess**: Status is set to final value ("running", "stopped", "error") after VBoxManage returns.
3. **Concurrency guard**: If status is already "starting" or "stopping" on read, return 409 immediately.
4. **Error recovery**: `error_message` is cleared (set to null) when a successful start transitions the VM to "running".

---

## Pydantic Schemas (service layer)

### Request Schemas

```python
# VMCreate — already in models/schemas.py from spec 001
class VMCreate(BaseModel):
    name: str        # 1–50 chars, regex: [a-zA-Z0-9][a-zA-Z0-9 \-]{0,49}
    os:   str        # required, free text
    ram:  int        # 512–16384 MB

# VMActionRequest — NEW: added in this spec
class VMActionRequest(BaseModel):
    vm_id: str       # UUID string — validated as UUID by service layer
```

### Response Schema

```python
# VMResponse — already in models/schemas.py from spec 001
class VMResponse(BaseModel):
    id:            str
    user_id:       str
    name:          str
    os:            str
    ram:           int
    status:        str
    error_message: str | None
    created_at:    str
    updated_at:    str
```

### List Response

`GET /api/v1/vm` returns `list[VMResponse]`. An empty list is returned (not 404) when the user has no VMs.

---

## Operation → DB Writes Summary

| Operation     | DB Writes (in order)                                                                   |
|---------------|----------------------------------------------------------------------------------------|
| create_vm     | INSERT vms (after VBoxManage success) → INSERT logs                                   |
| start_vm      | UPDATE vms status='starting' → (VBoxManage) → UPDATE vms status='running'/'error' → INSERT logs |
| stop_vm       | UPDATE vms status='stopping' → (VBoxManage) → UPDATE vms status='stopped'/'error' → INSERT logs |
| delete_vm     | (VBoxManage) → DELETE vms → INSERT logs                                                |
| list_vms      | SELECT vms (no writes)                                                                 |
| get_vm_status | SELECT vms (no writes)                                                                 |

---

## Validation Summary

| Field      | Layer 1 (Pydantic)              | Layer 2 (DB constraint)                    |
|------------|---------------------------------|--------------------------------------------|
| name       | regex + length (1–50)           | NOT NULL only (length not enforced at DB)  |
| os         | required (non-empty)            | NOT NULL                                   |
| ram        | 512 ≤ ram ≤ 16384               | CHECK (ram >= 512 AND ram <= 16384)        |
| status     | Set by service layer only       | CHECK (status IN whitelist)                |
| vm_id      | UUID string format check        | FK constraint on vms.id                    |
