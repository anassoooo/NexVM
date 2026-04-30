# Contract — VM API (P2 additions)

**Base prefix**: `/api/v1/vm`
**Auth**: Bearer token required on all endpoints

---

## POST /modify — Modify VM hardware

**Request**: `{"vm_id": "<uuid>", "ram": 4096, "cpu": 4}` (at least one field required)

| Code | Meaning |
|---|---|
| 200 | Updated `VMResponse` |
| 409 | VM not stopped |
| 422 | No fields provided, or values out of range |

---

## POST /pause

**Request**: `{"vm_id": "<uuid>"}`

| Code | Meaning |
|---|---|
| 200 | `VMResponse` with `status: "paused"` |
| 409 | VM not running |

---

## POST /resume

**Request**: `{"vm_id": "<uuid>"}`

| Code | Meaning |
|---|---|
| 200 | `VMResponse` with `status: "running"` |
| 409 | VM not paused |

---

## POST /savestate

**Request**: `{"vm_id": "<uuid>"}`

| Code | Meaning |
|---|---|
| 200 | `VMResponse` with `status: "stopped"` |
| 409 | VM not running |

---

## POST /portfwd — Add NAT rule

**Request**: `{"vm_id": "<uuid>", "name": "http", "protocol": "tcp", "host_port": 8080, "guest_port": 80}`

| Code | Meaning |
|---|---|
| 200 | `VMResponse` with updated `nat_rules` |
| 409 | VM not stopped, or duplicate rule name |
| 422 | Port out of range |

---

## DELETE /portfwd — Remove NAT rule

**Request**: `{"vm_id": "<uuid>", "name": "http"}`

| Code | Meaning |
|---|---|
| 200 | `VMResponse` with updated `nat_rules` |
| 404 | Rule name not found |
| 409 | VM not stopped |

---

## GET /snapshots?vm_id=\<uuid\> — List snapshots

| Code | Meaning |
|---|---|
| 200 | `[SnapshotResponse, ...]` ordered by `created_at desc` |
| 404 | VM not found |

---

## POST /snapshot — Take snapshot (status 201)

**Request**: `{"vm_id": "<uuid>", "name": "clean-install", "description": "optional"}`

| Code | Meaning |
|---|---|
| 201 | `SnapshotResponse` |
| 409 | VM not stopped, or duplicate snapshot name |

---

## POST /snapshot/restore — Restore snapshot

**Request**: `{"vm_id": "<uuid>", "name": "clean-install"}`

| Code | Meaning |
|---|---|
| 200 | `VMResponse` |
| 404 | Snapshot not found |
| 409 | VM not stopped |

---

## DELETE /snapshot — Delete snapshot

**Request**: `{"vm_id": "<uuid>", "name": "clean-install"}`

| Code | Meaning |
|---|---|
| 204 | No content |
| 404 | Snapshot not found |
| 409 | VM not stopped |

---

## Updated VMResponse

```json
{
  "...": "existing fields",
  "nat_rules": [
    {"name": "ssh", "protocol": "tcp", "host_port": 2222, "guest_port": 22}
  ]
}
```

## SnapshotResponse

```json
{
  "id": "<uuid>",
  "vm_id": "<uuid>",
  "name": "clean-install",
  "description": "Fresh Ubuntu install",
  "created_at": "2026-04-30T00:00:00Z"
}
```
