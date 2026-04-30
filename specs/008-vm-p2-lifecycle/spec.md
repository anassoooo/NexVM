# Spec 008 — VM P2 Lifecycle

**Branch**: `004-analytics`
**Date**: 2026-04-30
**Priority**: P2 — lifecycle complet

## Overview

Five features that give users full control over a VM's lifecycle after creation:
modify hardware, pause/resume execution, save state to disk, manage NAT port
forwarding rules, and take/restore/delete snapshots.

---

## F1 — Modify VM (RAM / CPU)

### Problem

After creation, RAM and CPU cannot be changed without deleting and recreating the VM.

### Feature

Users can update a stopped VM's RAM and/or CPU count.
Disk resize is out of scope for this spec (requires complex VDI manipulation).

### Functional Requirements

| ID | Requirement |
|---|---|
| FR-101 | User can change a stopped VM's RAM (512–16384 MB) |
| FR-102 | User can change a stopped VM's CPU count (1–32) |
| FR-103 | At least one field (ram or cpu) must be provided |
| FR-104 | VM must be in `stopped` state — any other state returns HTTP 409 |
| FR-105 | DB is updated to reflect new values after success |
| FR-106 | Operation is logged to the `logs` table |

### Acceptance Criteria

- Modifying RAM/CPU on a stopped VM succeeds; `VMResponse` reflects new values
- Modifying a running VM returns HTTP 409
- Providing neither `ram` nor `cpu` returns HTTP 422
- RAM/CPU outside valid range returns HTTP 422

---

## F2 — Pause / Resume

### Problem

The only way to temporarily free resources is to stop the VM, losing its in-memory state.
VirtualBox supports pausing a running VM without powering it off.

### Feature

Users can pause a running VM (freeze execution, keep memory) and resume it.

### Functional Requirements

| ID | Requirement |
|---|---|
| FR-201 | User can pause a running VM — status becomes `paused` |
| FR-202 | User can resume a paused VM — status returns to `running` |
| FR-203 | Pausing a non-running VM returns HTTP 409 |
| FR-204 | Resuming a non-paused VM returns HTTP 409 |
| FR-205 | `VMResponse.status` includes `paused` as a valid value |
| FR-206 | Both operations are logged |

### Acceptance Criteria

- Pausing a running VM: status changes to `paused`
- Resuming a paused VM: status returns to `running`
- Pausing an already-paused VM: HTTP 409
- Frontend VM card shows Pause button when running, Resume button when paused

---

## F3 — Save State

### Problem

Stopping a VM loses its in-memory execution state.
VirtualBox `savestate` hibernates the VM to disk so it can be resumed later.

### Feature

Users can save the state of a running VM to disk. The VM powers off after saving.
Starting the VM again restores from the saved state (VirtualBox handles this natively).

### Functional Requirements

| ID | Requirement |
|---|---|
| FR-301 | User can save the state of a running VM |
| FR-302 | VM must be running — any other state returns HTTP 409 |
| FR-303 | After save state completes, VM status becomes `stopped` |
| FR-304 | Operation is logged |

### Acceptance Criteria

- Save state on a running VM succeeds; VM status becomes `stopped`
- Save state on a stopped/paused VM returns HTTP 409
- Starting the VM again after save state restores from saved state (VirtualBox behavior, no backend change needed)

---

## F4 — Port-Forwarding Management

### Problem

The SSH port `2222→22` is hardcoded at creation time. Users cannot add or remove
NAT port-forwarding rules after the VM is created.

### Feature

Users can add and remove NAT port-forwarding rules on a stopped VM.

### Functional Requirements

| ID | Requirement |
|---|---|
| FR-401 | User can add a NAT rule (name, protocol tcp/udp, host_port, guest_port) |
| FR-402 | User can remove a NAT rule by name |
| FR-403 | VM must be in `stopped` state for both operations |
| FR-404 | `host_port` must be in range 1024–65535 |
| FR-405 | `guest_port` must be in range 1–65535 |
| FR-406 | Rule name must be unique per VM |
| FR-407 | `VMResponse.nat_rules` lists all current rules for the VM |
| FR-408 | Both operations are logged |

### Acceptance Criteria

- Adding a rule on a stopped VM succeeds; rule appears in `VMResponse.nat_rules`
- Adding a duplicate rule name returns HTTP 409
- Removing a rule that does not exist returns HTTP 404
- VM not stopped returns HTTP 409
- Host port outside 1024–65535 returns HTTP 422

---

## F5 — Snapshots

### Problem

There is no way to checkpoint a VM state and roll back to it, making test
environments risky (one bad command can destroy the state permanently).

### Feature

Users can take named snapshots of a stopped VM, restore to a previous snapshot,
and delete snapshots they no longer need.

### Functional Requirements

| ID | Requirement |
|---|---|
| FR-501 | User can take a snapshot of a stopped VM with a name (1–50 chars) and optional description |
| FR-502 | User can restore a stopped VM to a named snapshot |
| FR-503 | User can delete a named snapshot from a stopped VM |
| FR-504 | VM must be in `stopped` state for all three operations |
| FR-505 | Snapshot names must be unique per VM |
| FR-506 | `GET /api/v1/vm/snapshots` returns all snapshots for a given VM |
| FR-507 | All three operations are logged |

### Acceptance Criteria

- Taking a snapshot on a stopped VM succeeds; snapshot appears in list
- Taking a snapshot with a duplicate name returns HTTP 409
- Restoring a non-existent snapshot returns HTTP 404
- Restoring a VM that is not stopped returns HTTP 409
- Deleting a snapshot removes it from the list

---

## Out of Scope

- Disk resize (requires VDI modifymedium — deferred to P3)
- Live snapshots (VM running during snapshot — deferred to P3)
- Hot port-forward on running VM (controlvm natpf1 — deferred to P3)
- Snapshot tree/branching (VirtualBox supports it but MVP is linear)
- AI command support for P2 operations (deferred)
