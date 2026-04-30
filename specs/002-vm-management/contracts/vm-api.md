# Contract: VM API

**Branch**: `002-vm-management` | **Date**: 2026-04-06

This contract defines all VM endpoints — their request/response shapes, status codes, and error responses. All future feature plans that call VM endpoints must conform to this contract.

---

## Auth

All endpoints require:

```http
Authorization: Bearer <access_token>
```

Where `<access_token>` is a valid, non-expired Supabase JWT. Missing or invalid tokens return HTTP 401 (per `contracts/jwt-auth.md` from spec 001).

---

## Endpoints

### POST /api/v1/vm/create

Create and register a new VM.

**Request body**:

```json
{
  "name": "my-ubuntu-vm",
  "os":   "Ubuntu 22.04",
  "ram":  2048
}
```

| Field | Type   | Required | Constraints                                    |
|-------|--------|----------|------------------------------------------------|
| name  | string | YES      | 1–50 chars; alphanumeric, hyphens, spaces only |
| os    | string | YES      | Non-empty free text                            |
| ram   | int    | YES      | 512–16384 (inclusive)                          |

**Success response** — HTTP 201:

```json
{
  "id":            "uuid",
  "user_id":       "uuid",
  "name":          "my-ubuntu-vm",
  "os":            "Ubuntu 22.04",
  "ram":           2048,
  "status":        "stopped",
  "error_message": null,
  "created_at":    "2026-04-06T10:00:00Z",
  "updated_at":    "2026-04-06T10:00:00Z"
}
```

**Error responses**:

| Scenario                          | Status | Body                                                    |
|-----------------------------------|--------|---------------------------------------------------------|
| Missing/invalid JWT               | 401    | `{"detail": "Invalid or expired token"}`                |
| Name validation failed            | 422    | Pydantic validation error body                          |
| RAM out of range                  | 422    | Pydantic validation error body                          |
| Name already registered in VBox   | 409    | `{"detail": "A VM with this name already exists"}`      |
| VBoxManage failed                 | 500    | `{"detail": "VBoxManage failed: <stderr>"}`             |
| VBoxManage not reachable          | 503    | `{"detail": "VBoxManage not reachable"}`                |

---

### GET /api/v1/vm

List all VMs belonging to the authenticated user.

**Request body**: None

**Success response** — HTTP 200:

```json
[
  {
    "id":            "uuid",
    "user_id":       "uuid",
    "name":          "my-ubuntu-vm",
    "os":            "Ubuntu 22.04",
    "ram":           2048,
    "status":        "stopped",
    "error_message": null,
    "created_at":    "2026-04-06T10:00:00Z",
    "updated_at":    "2026-04-06T10:00:00Z"
  }
]
```

Returns an empty array `[]` when the user has no VMs (not 404).

---

### POST /api/v1/vm/status

Get the current DB-record status of a specific VM.

**Request body**:

```json
{ "vm_id": "uuid" }
```

**Success response** — HTTP 200: same shape as a single `VMResponse` object.

**Error responses**:

| Scenario            | Status | Body                          |
|---------------------|--------|-------------------------------|
| VM not found / wrong user | 404 | `{"detail": "VM not found"}` |

---

### POST /api/v1/vm/start

Start a stopped or errored VM.

**Request body**:

```json
{ "vm_id": "uuid" }
```

**Success response** — HTTP 200:

```json
{ ..., "status": "running", "error_message": null }
```

**Error responses**:

| Scenario                          | Status | Body                                                      |
|-----------------------------------|--------|-----------------------------------------------------------|
| VM not found / wrong user         | 404    | `{"detail": "VM not found"}`                              |
| VM in transitional state          | 409    | `{"detail": "VM is already in a transitional state"}`     |
| VM not in startable state         | 409    | `{"detail": "Cannot start VM in '<status>' state"}`       |
| VBoxManage failed                 | 500    | `{"detail": "VBoxManage failed: <stderr>"}`               |
| VBoxManage timed out              | 500    | `{"detail": "VBoxManage command timed out"}`              |

---

### POST /api/v1/vm/stop

Stop a running VM.

**Request body**:

```json
{ "vm_id": "uuid" }
```

**Success response** — HTTP 200:

```json
{ ..., "status": "stopped", "error_message": null }
```

**Error responses**:

| Scenario                          | Status | Body                                                      |
|-----------------------------------|--------|-----------------------------------------------------------|
| VM not found / wrong user         | 404    | `{"detail": "VM not found"}`                              |
| VM in transitional state          | 409    | `{"detail": "VM is already in a transitional state"}`     |
| VM not running                    | 409    | `{"detail": "Cannot stop VM in '<status>' state"}`        |
| VBoxManage failed                 | 500    | `{"detail": "VBoxManage failed: <stderr>"}`               |
| VBoxManage timed out              | 500    | `{"detail": "VBoxManage command timed out"}`              |

---

### POST /api/v1/vm/delete

Delete a stopped VM.

**Request body**:

```json
{ "vm_id": "uuid" }
```

**Success response** — HTTP 200:

```json
{ "detail": "VM deleted" }
```

**Error responses**:

| Scenario                          | Status | Body                                                           |
|-----------------------------------|--------|----------------------------------------------------------------|
| VM not found / wrong user         | 404    | `{"detail": "VM not found"}`                                   |
| VM not stopped                    | 409    | `{"detail": "Cannot delete VM in '<status>' state — stop it first"}` |
| VBoxManage failed                 | 500    | `{"detail": "VBoxManage failed: <stderr>"}`                    |

---

## Common Patterns

### All 4xx/5xx responses share the shape:

```json
{ "detail": "<human-readable message>" }
```

### `updated_at` field

Updated by the service layer on every status change (not a DB trigger). The service explicitly sets `updated_at = now()` on every `UPDATE vms` call.

### VM ownership enforcement

The service layer queries `vms` with both `id = vm_id` AND `user_id = current_user_id`. A missing result (whether the VM doesn't exist or belongs to another user) always returns 404. 403 is never returned for VM operations.
