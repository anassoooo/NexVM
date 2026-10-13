# Spec 012 — Security Hardening

**Branch**: `012-security-hardening`
**Date**: 2026-10-13
**Priority**: P0 — data loss and host compromise risks
**Constitution**: v1.1.0 (§VII, §IX, §XI.4–§XI.7 were added for this spec)

## Overview

A code review on 2026-10-13 found that users of a shared NexVM host can destroy each
other's VMs, read and write arbitrary files on the host, freeze the API for everyone, and
see every user's VM list without logging in. This spec fixes those issues and three smaller
ones. It adds no new user-facing features except a confirmation step for AI deletions.

Already fixed before this spec (not in scope): Data API write grants (migration 004) and the
shared Supabase client switching to user JWTs after login (commit `04c4415`).

---

## F1 — VirtualBox Resource Isolation (P0)

### Problem

VMs are addressed in VBoxManage by their user-facing `name`, which is global on the host.
When `createvm` reports "already exists", `_run_vbox` treats the existing VM as an orphan,
unregisters it and deletes its folder (`vm_service.py:110`). If user B creates a VM with the
same name as user A's, A's VM and disk are destroyed. Two users with the same VM name would
also control the same VirtualBox machine. Disk paths are derived from the name too.

### Feature

VMs get a host-unique VirtualBox name at creation and are addressed by `vbox_id` afterwards.
The orphan auto-purge is removed.

### Functional Requirements

| ID | Requirement |
|---|---|
| FR-101 | `create_vm`, `clone_vm` and `import_ova` register the VM as `<name>-<8 hex chars>` (random) |
| FR-102 | The VDI disk path uses the host-unique name, not the display name |
| FR-103 | Every VBoxManage call on an existing VM uses `vm["vbox_id"]`; a row without one returns 409 (never falls back to the display name) |
| FR-107 | If the new VM's UUID can't be read after create/clone/import, the VM is unregistered by its host-unique name and the call returns 500 |
| FR-104 | The "already exists → unregister + rmtree" branch in `_run_vbox` is removed; the error is returned as HTTP 409 |
| FR-105 | The display `name` stored in the database and shown in the UI is unchanged |
| FR-106 | Existing VMs keep working with no data migration (all 4 have `vbox_id`) |

### Acceptance Criteria

- Two different users can each create a VM named `ubuntu`; both VMs exist afterwards
- A test asserts that no `unregistervm` call is ever made during `create_vm`
- Start/stop/delete/snapshot/etc. pass the `vbox_id` UUID to VBoxManage
- `createvm` failing with "already exists" returns HTTP 409 and touches nothing on disk

---

## F2 — Host Filesystem Confinement (P0)

### Problem

`iso_path`, `output_path` and `source_path` are only checked for being absolute with the
right extension (`schemas.py:65,150,166`). Any user can make the backend export an OVA to any
folder, or import or attach any file on the host.

### Feature

Each path must resolve inside a configured directory.

### Functional Requirements

| ID | Requirement |
|---|---|
| FR-201 | New settings `ISO_DIR` and `EXPORT_DIR`; defaults `<VM storage>/isos` and `<VM storage>/exports`, created at startup |
| FR-202 | `iso_path` must resolve (via `os.path.realpath`) inside `ISO_DIR` |
| FR-203 | `output_path` and `source_path` are bare file names (`my-vm.ova`); the server reads and writes them in `EXPORT_DIR/<user_id>/`, so users can't reach each other's exports |
| FR-204 | `..` segments and symlinks pointing outside the directory are rejected |
| FR-205 | Rejection returns HTTP 422 with a message naming the allowed directory |
| FR-206 | The AI `attach_iso` path goes through the same check |
| FR-207 | `.env.example` files and the frontend placeholders document the two directories |

### Acceptance Criteria

- `C:\Windows\x.ova` as export target → 422
- `../x.ova` or `sub/x.ova` as export name → 422
- Importing a file that exists only in another user's folder → 404
- `<ISO_DIR>\ubuntu.iso` → accepted
- Existing ISO/export flows work when files are placed in the configured directories

---

## F3 — Non-blocking API (P1)

### Problem

All route handlers are `async def` but call blocking code (VBoxManage subprocesses with
timeouts up to minutes, the synchronous Supabase client, Groq). One long clone or export
freezes every other request, including logins.

### Functional Requirements

| ID | Requirement |
|---|---|
| FR-301 | Route handlers in `vm`, `admin_vm`, `ai`, `analytics`, `logs`, `schedules` and `auth` are `def` |
| FR-302 | `get_current_user` and `get_current_admin_user` are `def` |
| FR-303 | `health_check` may stay `async` (it already uses `asyncio.to_thread`) |

### Acceptance Criteria

- While a request is blocked in a slow VBoxManage call, `GET /api/v1/health` still answers
  (verified with a test that patches `run_vbox_command` to sleep)
- All existing tests pass

---

## F4 — Remove Public VM Listing (P1)

### Problem

`GET /api/v1/vm/public` returns every user's VMs (names, OS, ISO paths, VRDE ports) with no
authentication. Nothing in the frontend uses it. It violates §II.

### Functional Requirements

| ID | Requirement |
|---|---|
| FR-401 | The route is deleted; `GET /api/v1/vm/public` returns 404/405 |
| FR-402 | Admins keep the full list via `GET /api/v1/admin/vm/` |

---

## F5 — AI Delete Confirmation (P1)

### Problem

When the model returns `delete_vm`, the backend deletes immediately (`ai_service.py:404`).
A misread prompt deletes a VM with no way back.

### Feature

The AI proposes the deletion; the user confirms it in the chat.

### Functional Requirements

| ID | Requirement |
|---|---|
| FR-501 | For `delete_vm`, `process_ai_command` does not call `vm_service.delete_vm` |
| FR-502 | `AICommandResponse` gains `pending_action: {action, vm_id, vm_name} \| null` |
| FR-503 | The reply asks "Delete VM '<name>'? This cannot be undone." |
| FR-504 | The chat shows Confirm / Cancel buttons for a pending action |
| FR-505 | Confirm calls `POST /api/v1/vm/delete` (existing ownership checks and logging apply) |
| FR-506 | Cancel adds a "Cancelled" message and calls nothing |
| FR-507 | The proposal is logged to `ai_usage` as today (§XII.2) |

### Acceptance Criteria

- An AI `delete_vm` response leaves the VM untouched and returns `pending_action`
- Confirm deletes the VM; Cancel does not
- A pending action for a VM the user does not own fails at confirm time with 404

---

## F6 — No Fixed Host Port per VM (P2)

### Problem

Every VM is created with NAT rule `ssh,tcp,,2222,,22` (`vm_service.py:304`). Only one running
VM can bind host port 2222; the rest silently lose SSH forwarding. `add_port_rule` also does
not check host ports used by other VMs.

### Functional Requirements

| ID | Requirement |
|---|---|
| FR-601 | New VMs are created with a NAT adapter and no default port rule |
| FR-602 | `add_port_rule` rejects a `host_port` already used by any VM's `nat_rules` or `vrde_port` with HTTP 409 |

---

## F7 — Drop Per-request Profile Check (P2)

### Problem

`get_current_user` runs `ensure_profile_exists` (a SELECT, sometimes an INSERT) on every
authenticated request. The `on_auth_user_created` trigger already creates profiles.

### Functional Requirements

| ID | Requirement |
|---|---|
| FR-701 | `get_current_user` no longer queries `profiles` |
| FR-702 | Code that reads a profile tolerates a missing row (treats it as non-admin) |

---

## F8 — CLI Argument Safety (P2)

### Problem

Snapshot names and port-rule names only have length limits. A name starting with `-` can be
parsed by VBoxManage as an option, and a port-rule name containing `,` changes the meaning
of the `--natpf1` rule string.

### Functional Requirements

| ID | Requirement |
|---|---|
| FR-801 | Snapshot and port-rule names must match `^[A-Za-z0-9][A-Za-z0-9 _.-]{0,49}$` |
| FR-802 | Invalid names return HTTP 422 |

---

## Out of Scope

- Redis-backed AI rate limit (single-process deployment is the target)
- Moving existing ISOs/OVAs into the new directories (documented as a manual step)
- Renaming existing VirtualBox VMs to the new naming scheme
- Docker `.env` setup and recording migration 003 in Supabase history (housekeeping)
