# Spec 007 — VM P1 Features: ISO, VRDE, Auto-polling

**Branch**: `004-analytics`
**Date**: 2026-04-30
**Priority**: P1 — critical for usability

## Overview

Three features that make the VM module actually usable after creation.
Currently, VMs boot into void (no OS), cannot be interacted with remotely,
and transitional states (`starting`/`stopping`) never resolve without a manual sync.

---

## F1 — ISO / Boot Media

### Problem

VMs are created with a disk but no bootable media. They launch into a BIOS
boot loop with no operating system to install.

### Feature

Users can attach an ISO image (stored on the host) to a VM's IDE controller
so the VM boots from it. The ISO can also be detached once the OS is installed.

### Functional Requirements

| ID | Requirement |
|---|---|
| FR-101 | User can attach an ISO to a stopped VM by providing the absolute path to the ISO file on the host |
| FR-102 | User can detach the ISO from a stopped VM |
| FR-103 | VM must be in `stopped` state to attach or detach — any other state returns an error |
| FR-104 | The ISO path must exist on the host filesystem — a missing path returns an error |
| FR-105 | `VMResponse` includes `iso_path` (string or null) reflecting the current state |
| FR-106 | Attaching/detaching is logged to the `logs` table |

### Acceptance Criteria

- Attaching a valid ISO to a stopped VM succeeds and `VMResponse.iso_path` is non-null
- Attaching to a running/starting/stopping VM returns HTTP 409
- Attaching a non-existent path returns HTTP 422
- Detaching a VM that has no ISO attached returns HTTP 409
- After detach, `VMResponse.iso_path` is null

---

## F2 — VRDE Remote Access

### Problem

There is no way to interact with a running VM's display or console.
VirtualBox ships VRDE (VirtualBox Remote Desktop Extension) which exposes
a Remote Desktop Protocol port that any RDP client can connect to.

### Feature

Users can enable VRDE on a stopped VM specifying a port number.
The VRDE port is saved and displayed on the VM card so the user knows
where to connect with an RDP client (e.g. Windows Remote Desktop, Remmina).

### Functional Requirements

| ID | Requirement |
|---|---|
| FR-201 | User can enable VRDE on a stopped VM by providing a port (1024–65535) |
| FR-202 | User can disable VRDE on a stopped VM |
| FR-203 | VM must be in `stopped` state to enable or disable VRDE |
| FR-204 | The requested port must not already be in use by another VM in the system |
| FR-205 | `VMResponse` includes `vrde_enabled` (bool) and `vrde_port` (int or null) |
| FR-206 | Enabling/disabling VRDE is logged to the `logs` table |

### Acceptance Criteria

- Enabling VRDE on a stopped VM with a free port succeeds; `vrde_enabled=true`, `vrde_port=<n>`
- Enabling VRDE on a running VM returns HTTP 409
- Using an already-taken port returns HTTP 409
- Port outside 1024–65535 returns HTTP 422
- Disabling VRDE on a VM where VRDE is already off returns HTTP 409
- After disable, `vrde_enabled=false`, `vrde_port=null`

---

## F3 — Auto-polling Status

### Problem

When a VM enters `starting` or `stopping`, its status never updates automatically.
The user must click Sync manually to see if the VM has finished transitioning.

### Feature

The frontend polls the VM list every 5 seconds whenever any VM is in a
transitional state (`starting` or `stopping`). Polling stops automatically
when all VMs reach a stable state.

### Functional Requirements

| ID | Requirement |
|---|---|
| FR-301 | When at least one VM has status `starting` or `stopping`, the frontend polls every 5 seconds |
| FR-302 | Polling stops when no VM is in a transitional state |
| FR-303 | Polling uses the existing `GET /api/v1/vm` endpoint — no new endpoint |
| FR-304 | Polling must not fire if the component is unmounted (no memory leaks) |
| FR-305 | The UI must not visually flicker during background polls |

### Acceptance Criteria

- Starting a VM triggers polling; the card status updates to `running` without manual Sync
- Stopping a VM triggers polling; the card status updates to `stopped` without manual Sync
- Once all VMs are stable, network requests stop
- Unmounting the component while polling is active produces no console errors

---

## Out of Scope

- Hot-attach ISO to a running VM (requires `controlvm`; deferred to P2)
- VRDE authentication / password (VirtualBox handles this natively; not in MVP)
- Auto-assignment of a free VRDE port (user specifies port; MVP)
- AI command support for ISO / VRDE (no AI action schemas in this spec)
