# Feature Specification: VM Management

**Feature Branch**: `002-vm-management`  
**Created**: 2026-04-06  
**Status**: Draft  
**Input**: `docs/implementation-plan.md` — "VM Control" vertical slice  
**Depends on**: `001-supabase-auth-db` (auth, schema, RLS — must be complete)

---

## Overview

This is the **core operational feature** of myVMS. With auth established, users can now register, start, stop, and delete VirtualBox virtual machines through the web interface. This spec covers the complete VM lifecycle — from creation to deletion — including state transitions, VBoxManage integration, frontend controls, and audit logging for every action.

All VM operations execute synchronously within the HTTP request lifecycle. VBoxManage is invoked as a subprocess on the host machine running the backend.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Create and Register a VM (Priority: P1)

A user wants to add a new virtual machine to the system. They provide a name, select an operating system label, and set a RAM allocation. The system registers the VM in VirtualBox and adds a record to the database.

**Why this priority**: Every other VM action (start, stop, delete) requires an existing VM record. This is the entry point for the entire feature.

**Independent Test**: Can be fully tested by submitting a create request and confirming the VM appears in the VMs page, the database record exists, and VBoxManage confirms the VM is registered — without starting or stopping it.

**Acceptance Scenarios**:

1. **Given** a logged-in user on the VMs page, **When** they submit a valid name, OS, and RAM, **Then** a VM record is created with status "stopped", VBoxManage registers the VM, and it appears in the VM list.
2. **Given** a user submitting a VM name, **When** the name is fewer than 1 or more than 50 characters, **Then** the request is rejected with a validation error before any VBoxManage call is made.
3. **Given** a user submitting RAM, **When** the value is outside 512–16384 MB, **Then** the request is rejected with a validation error before any VBoxManage call is made.
4. **Given** a user submitting a name, **When** that name is already registered in VirtualBox, **Then** the request is rejected with a clear conflict error and no duplicate DB record is created.
5. **Given** VBoxManage failing during creation, **Then** no DB record is created, the failure is logged, and the user receives an error response with an actionable message.

---

### User Story 2 — Start and Stop a VM (Priority: P1)

A user can start a VM that is stopped and stop a VM that is running. The status updates in the VM list. During transitional states, action buttons are disabled so the user cannot trigger concurrent operations.

**Why this priority**: Start and stop are the primary operational actions. Without them the VM list is a read-only display with no utility.

**Independent Test**: Can be tested by creating a VM, clicking Start, verifying the status moves to "running", clicking Stop, and verifying the status returns to "stopped" — without requiring delete or AI features.

**Acceptance Scenarios**:

1. **Given** a VM in "stopped" status, **When** the user clicks Start, **Then** the status immediately moves to "starting", VBoxManage `startvm --type headless` is executed, and the status updates to "running" on success.
2. **Given** a VM in "running" status, **When** the user clicks Stop, **Then** the status immediately moves to "stopping", VBoxManage `controlvm poweroff` is executed, and the status updates to "stopped" on success.
3. **Given** a VM in "starting" or "stopping" status, **When** the user views the VM list, **Then** action buttons (Start, Stop, Delete) for that VM are visually disabled.
4. **Given** VBoxManage failing during start or stop, **Then** the VM is set to "error" status, the stderr output is stored in `error_message`, the failure is logged, and an error response is returned.
5. **Given** VBoxManage timing out (> 30 seconds), **Then** the VM is set to "error" status with message "Command timed out", the timeout is logged, and an error response is returned.
6. **Given** a VM in "error" status, **When** the user clicks Start, **Then** the system treats it as a retry — status moves to "starting" and the start flow begins again.

---

### User Story 3 — Delete a VM (Priority: P2)

A user can permanently delete a VM they own. The VM is unregistered from VirtualBox (disk files deleted) and removed from the database.

**Why this priority**: Delete is needed for cleanup and lifecycle completion, but it is not required to demonstrate core VM control. Create + Start + Stop covers the P1 MVP.

**Independent Test**: Can be tested by stopping a running VM, clicking Delete, confirming it disappears from the VM list, and verifying VBoxManage no longer lists it.

**Acceptance Scenarios**:

1. **Given** a VM in "stopped" status, **When** the user confirms deletion, **Then** VBoxManage `unregistervm --delete` is executed and the DB record is removed on success.
2. **Given** a VM in "running", "starting", or "stopping" status, **When** the user attempts deletion, **Then** the request is rejected with HTTP 409 — only stopped VMs can be deleted.
3. **Given** VBoxManage failing during deletion, **Then** the DB record is NOT removed, the failure is logged with error details, and the user receives an error message.
4. **Given** a user who knows the UUID of another user's VM, **When** they attempt to delete it via the API, **Then** the request returns 404 — no existence is leaked and no action is taken.

---

### User Story 4 — View VM List and Status (Priority: P1)

A user can see all their VMs with name, OS, RAM, and current status. Status badges are color-coded to communicate health at a glance. The list reflects the current state after any action.

**Why this priority**: The VM list is the primary UI surface. All other actions are taken from it. It must work before any other story can be tested end-to-end.

**Independent Test**: Can be tested by creating VMs via the API and verifying the VMs page renders each with correct status badges — no start/stop/delete required.

**Acceptance Scenarios**:

1. **Given** a logged-in user with no VMs, **When** they visit `/vms`, **Then** an empty state message is shown.
2. **Given** a logged-in user with VMs, **When** they visit `/vms`, **Then** each VM is shown with its name, OS, RAM, and a color-coded status badge.
3. **Given** two users each with their own VMs, **When** User A views `/vms`, **Then** only User A's VMs appear — none of User B's.
4. **Given** a VM whose status changed (e.g., from starting to running), **When** the user refreshes or triggers an action, **Then** the updated status is reflected.

---

### Edge Cases

- **VBoxManage not installed**: `GET /api/v1/health` detects and reports this. VM create/start/stop/delete return `503 Service Unavailable` with message "VBoxManage not reachable" — no silent failures.
- **Concurrent start on same VM**: The second request finds the VM already in "starting" state and returns HTTP 409 Conflict immediately — no duplicate VBoxManage calls.
- **VM name with special characters**: Names are validated at the API boundary (alphanumeric, hyphens, spaces only). The validated name is passed as a list argument to subprocess — no shell interpolation occurs.
- **VBoxManage succeeds but DB write fails**: The VM exists in VirtualBox but the status update is lost. The VM stays in its previous DB state. The mismatch is logged. A future `showvminfo` call can reconcile.
- **User deletes their account while a VM is running**: Cascade DELETE on the `vms` table removes all DB records. The VirtualBox VM continues running on the host until the admin manually cleans it up — this is a known limitation for single-tenant MVP.
- **RAM at boundary values (512, 16384)**: Both are valid. 511 and 16385 are rejected by the API validator and the DB CHECK constraint as a second line of defense.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow authenticated users to create a VM by specifying a name (1–50 characters, alphanumeric + hyphens + spaces only), an operating system label (free text, required), and RAM in MB (integer, 512–16384 inclusive).
- **FR-002**: System MUST register the VM in VirtualBox via `VBoxManage createvm --name <name> --register` on creation. If VBoxManage fails, no DB record is created.
- **FR-003**: System MUST store the VM record in the database with `status = 'stopped'` after successful VBoxManage registration.
- **FR-004**: System MUST reject VM creation when the name already exists in VirtualBox, returning HTTP 409 with message "A VM with this name already exists".
- **FR-005**: System MUST allow authenticated users to start a VM whose status is "stopped" or "error". The status MUST be set to "starting" in the database before the VBoxManage call is made.
- **FR-006**: System MUST execute `VBoxManage startvm <name> --type headless` when starting a VM. On success, set status to "running". On failure, set status to "error" and store stderr in `error_message`.
- **FR-007**: System MUST allow authenticated users to stop a VM whose status is "running". The status MUST be set to "stopping" in the database before the VBoxManage call is made.
- **FR-008**: System MUST execute `VBoxManage controlvm <name> poweroff` when stopping a VM. On success, set status to "stopped". On failure, set status to "error" and store stderr in `error_message`.
- **FR-009**: System MUST reject start/stop actions on VMs in "starting" or "stopping" states with HTTP 409 Conflict.
- **FR-010**: System MUST allow authenticated users to delete a VM only when its status is "stopped". Deletion requests on any other status MUST be rejected with HTTP 409.
- **FR-011**: System MUST execute `VBoxManage unregistervm <name> --delete` on deletion. The DB record MUST be removed only after VBoxManage succeeds. On VBoxManage failure, the DB record is preserved and an error is returned.
- **FR-012**: System MUST allow authenticated users to list all their own VMs, returning name, OS, RAM, status, error_message, created_at, and updated_at for each.
- **FR-013**: System MUST enforce a 30-second timeout on every VBoxManage subprocess call. On timeout, set the VM to "error" status with `error_message = "Command timed out"`.
- **FR-014**: System MUST log every VM action (create, start, stop, delete) to the `logs` table before returning the HTTP response — including on failure.
- **FR-015**: System MUST enforce that each user can only read, modify, and delete their own VM records. Requests targeting another user's VM MUST return HTTP 404.
- **FR-016**: System MUST validate VM name at the API boundary: 1–50 characters, alphanumeric, hyphens, and spaces only. Names failing this rule are rejected before any VBoxManage call.
- **FR-017**: System MUST only invoke five whitelisted VBoxManage subcommands: `createvm`, `startvm`, `controlvm`, `unregistervm`, `showvminfo`. No other subcommands are permitted.
- **FR-018**: System MUST display the VM list with color-coded status badges: green (running), grey (stopped), amber (starting/stopping), red (error).
- **FR-019**: System MUST disable VM action buttons (Start, Stop, Delete) in the UI when the VM is in "starting" or "stopping" state.
- **FR-020**: System MUST display VM `error_message` in the UI when a VM is in "error" state so the user knows what failed.

### Key Entities

- **VM**: Represents a VirtualBox virtual machine managed by the system. Belongs to one User. Has a name (unique in VirtualBox), OS label, RAM, and a lifecycle status. May carry an error message when in a failed state. The database record is the source of truth for status during operations; VirtualBox is the execution target.
- **VBoxManage Command**: A subprocess call to the VirtualBox management CLI. Always invoked with a fixed set of arguments from a hardcoded map. Never constructed from raw user input. Wrapped with a 30-second timeout and structured error capture.
- **Log**: Reused from spec 001. Every VM action generates one log entry. The `target` field carries the VM's UUID. The `action` field carries one of the five whitelisted VM actions.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can create a VM, and `VBoxManage list vms` confirms it is registered within 10 seconds of the API response.
- **SC-002**: 100% of VM actions (create, start, stop, delete) produce a log entry in the `logs` table before the HTTP response is returned — verified by checking log count after each action.
- **SC-003**: A started VM transitions through "stopped" → "starting" → "running" with correct DB updates at each step — verified by `pytest test_vm_service.py`.
- **SC-004**: A stopped VM transitions through "running" → "stopping" → "stopped" with correct DB updates at each step — verified by `pytest test_vm_service.py`.
- **SC-005**: VBoxManage failures (non-zero exit code) result in the VM being set to "error" status with stderr captured in `error_message` — 0 silent failures.
- **SC-006**: All VBoxManage calls complete or time out within 30 seconds — no subprocess hangs indefinitely.
- **SC-007**: A request targeting another user's VM UUID returns 404 — 0 cross-user data exposures.
- **SC-008**: `pytest backend/tests/test_vm_service.py` passes all test cases with mocked VBoxManage.

---

## Assumptions

- VirtualBox is installed on the host machine running the FastAPI backend. `VBoxManage` is accessible via `PATH` or the `VBOXMANAGE_PATH` environment variable.
- Single-tenant deployment: one VirtualBox host. No per-user VM quotas or resource limits for MVP.
- VM creation configures **name and RAM only**. Disk storage, network adapters, and display configuration are out of scope for MVP. The VM is registered and can be started/stopped, but it will not be a fully configured guest OS until those are set up externally.
- VM names must be unique across VirtualBox (not just per user), because VBoxManage enforces global uniqueness. The API reflects this by rejecting duplicate names with 409.
- The `os` field is a free-text label (e.g., "Ubuntu 22.04"). It is not validated against VirtualBox's guest OS type list for MVP.
- "Delete" is destructive: `--delete` removes the VM's disk files from the host. There is no soft delete or recycle bin.
- Status synchronization with VirtualBox is not real-time. The DB is the authoritative source of truth for status. `showvminfo` is only used by the health check and manual reconciliation — not by normal CRUD operations.
- All VBoxManage calls run synchronously within the FastAPI request. No background task queue for MVP.
- The frontend refetches the VM list on every user action (create, start, stop, delete). No real-time polling or WebSocket updates for MVP.

---

## Clarifications

### Session 2026-04-06

- Q: Should VM creation configure disk, network, and display? → A: No. MVP creates and registers the VM with a name and RAM only. All other hardware configuration is out of scope for this spec.
- Q: Should start/stop/delete be synchronous or asynchronous? → A: Synchronous for MVP. VBoxManage calls happen within the request with a 30-second timeout.
- Q: What `--type` should be used for `startvm`? → A: `headless` — no display window required.
- Q: Should duplicate VM names be rejected? → A: Yes — VBoxManage enforces global uniqueness. The API should detect this and return 409 with a clear message.
- Q: Should the frontend poll for live status updates? → A: No polling for MVP. The frontend refetches after each user action.
- Q: What happens to a VM in "error" state — can the user retry start? → A: Yes. "error" → "starting" is a valid transition for retry. The error_message is cleared on the next successful start.
