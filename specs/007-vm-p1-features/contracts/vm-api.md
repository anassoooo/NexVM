# Contract — VM API (P1 additions)

**Base prefix**: `/api/v1/vm`
**Auth**: Bearer token required on all endpoints

---

## POST /iso — Attach ISO

**Request body**:
```json
{
  "vm_id": "<uuid>",
  "iso_path": "<absolute path ending in .iso>"
}
```

**Responses**:
| Code | Meaning |
|---|---|
| 200 | Success — returns updated `VMResponse` |
| 409 | VM not in `stopped` state |
| 422 | `iso_path` invalid (not absolute, not `.iso`, or file not found) |
| 401 | Missing / invalid token |
| 404 | VM not found |

---

## DELETE /iso — Detach ISO

**Request body**:
```json
{ "vm_id": "<uuid>" }
```

**Responses**:
| Code | Meaning |
|---|---|
| 200 | Success — returns updated `VMResponse` with `iso_path: null` |
| 409 | VM not stopped, or `iso_path` already null |
| 401 | Missing / invalid token |
| 404 | VM not found |

---

## POST /vrde — Enable VRDE

**Request body**:
```json
{
  "vm_id": "<uuid>",
  "port": 3389
}
```

Constraints: `port` ∈ [1024, 65535].

**Responses**:
| Code | Meaning |
|---|---|
| 200 | Success — returns updated `VMResponse` with `vrde_enabled: true` |
| 409 | VM not stopped, or port already used by another VM |
| 422 | Port out of range |
| 401 | Missing / invalid token |
| 404 | VM not found |

---

## DELETE /vrde — Disable VRDE

**Request body**:
```json
{ "vm_id": "<uuid>" }
```

**Responses**:
| Code | Meaning |
|---|---|
| 200 | Success — returns updated `VMResponse` with `vrde_enabled: false, vrde_port: null` |
| 409 | VM not stopped, or VRDE already disabled |
| 401 | Missing / invalid token |
| 404 | VM not found |

---

## Updated VMResponse schema

```json
{
  "id": "<uuid>",
  "user_id": "<uuid>",
  "name": "my-vm",
  "os": "ubuntu 22.04",
  "ram": 2048,
  "cpu": 2,
  "disk_size": 20480,
  "vbox_id": "<vbox-uuid>",
  "status": "stopped",
  "error_message": null,
  "iso_path": "/path/to/ubuntu.iso",
  "vrde_enabled": true,
  "vrde_port": 3389,
  "created_at": "2026-04-30T00:00:00Z",
  "updated_at": "2026-04-30T00:00:00Z"
}
```
