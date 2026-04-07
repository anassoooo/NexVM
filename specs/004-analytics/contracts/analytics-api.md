# Contract: Analytics API

**Branch**: `004-analytics` | **Date**: 2026-04-07

This contract defines the analytics endpoints — their response shapes, status codes, and error responses. Future feature plans that consume analytics data must conform to this contract.

---

## Auth

All endpoints require:

```http
Authorization: Bearer <access_token>
```

Where `<access_token>` is a valid, non-expired Supabase JWT. Missing or invalid tokens return HTTP 403 (HTTPBearer) or HTTP 401.

---

## Endpoints

### GET /api/v1/analytics

Returns VM status counts and AI command count for the authenticated user.

**Request**: No body. Auth header required.

**Success response** — HTTP 200:

```json
{
  "total_vms": 3,
  "running_vms": 1,
  "stopped_vms": 2,
  "error_vms": 0,
  "total_ai_commands": 5
}
```

| Field             | Type | Description                                  |
|-------------------|------|----------------------------------------------|
| total_vms         | int  | Total VMs owned by the user                  |
| running_vms       | int  | VMs with status = "running"                  |
| stopped_vms       | int  | VMs with status = "stopped"                  |
| error_vms         | int  | VMs with status = "error"                    |
| total_ai_commands | int  | Total rows in ai_usage for this user         |

**Note**: VMs in `starting` or `stopping` states are included in `total_vms` but not in any sub-count field.

**Error responses**:

| Scenario            | Status | Body                                    |
|---------------------|--------|-----------------------------------------|
| Missing/invalid JWT | 403    | HTTPBearer default (or 401 from decode) |
| Supabase error      | 500    | `{"detail": "Analytics unavailable"}`   |

---

### GET /api/v1/analytics/admin

Returns system-wide metrics. Admin users only.

**Request**: No body. Auth header required. Caller must have `profiles.is_admin = true`.

**Success response** — HTTP 200:

```json
{
  "total_users": 2,
  "total_vms": 5,
  "running_vms": 2,
  "stopped_vms": 2,
  "error_vms": 1,
  "total_ai_commands": 10
}
```

| Field             | Type | Description                                     |
|-------------------|------|-------------------------------------------------|
| total_users       | int  | Total rows in profiles table                    |
| total_vms         | int  | Total VMs across all users                      |
| running_vms       | int  | VMs with status = "running" across all users    |
| stopped_vms       | int  | VMs with status = "stopped" across all users    |
| error_vms         | int  | VMs with status = "error" across all users      |
| total_ai_commands | int  | Total rows in ai_usage across all users         |

**Error responses**:

| Scenario              | Status | Body                                    |
|-----------------------|--------|-----------------------------------------|
| Missing/invalid JWT   | 403    | HTTPBearer default                      |
| Authenticated non-admin | 403  | `{"detail": "Admin access required"}`   |
| Supabase error        | 500    | `{"detail": "Analytics unavailable"}`   |

---

## Common Patterns

All 4xx/5xx responses share the shape:

```json
{ "detail": "<human-readable message>" }
```

Both endpoints are read-only — no state is mutated. Safe to call on every page load.
