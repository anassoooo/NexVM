# Feature Specification: VM Management

**Feature Branch**: `002-vm-management`  
**Created**: 2026-04-06  
**Status**: Draft  
**Input**: `docs/implementation-plan.md` — "VM Control" vertical slice  
**Depends on**: `001-supabase-auth-db` (auth, schema, RLS — must be complete)

---

## Overview

This is the **core operational feature** of myVMS. With auth established, users can register, start, stop, and delete VirtualBox virtual machines through two access paths:

- **Regular users** — interact exclusively through the AI chat interface (`/ai`). The AI assistant interprets natural language commands and calls the VM management API on the user's behalf.
- **Admin users** — manage all users' VMs through the traditional admin panel (`/admin/vms`) with a structured VM list, status badges, and action controls.

This spec covers the complete VM lifecycle — from creation to deletion — including state transitions, VBoxManage integration, audit logging, and the admin frontend. The AI chat UX is covered in spec 003.

All VM operations execute synchronously within the HTTP request lifecycle. VBoxManage is invoked as a subprocess on the host machine running the backend.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Create and Register a VM (Priority: P1)

An authenticated user (via AI chat command or admin panel) submits a VM creation request with a name, OS label, and RAM allocation. The system validates the input, registers the VM in VirtualBox, and adds a record to the database.

**Why this priority**: Every other VM action (start, stop, delete) requires an existing VM record. This is the entry point for the entire feature.

**Independent Test**: Can be fully tested by submitting a create request (via API directly, AI command, or admin panel) and confirming the database record exists and VBoxManage confirms registration — without starting or stopping it.

**Acceptance Scenarios**:

1. **Given** an authenticated user submitting a valid name, OS, and RAM via API, **When** the request is received, **Then** a VM record is created with status "stopped", VBoxManage registers the VM, and the record is retrievable via `GET /api/v1/vms`.
2. **Given** a user submitting a VM name, **When** the name is fewer than 1 or more than 50 characters, **Then** the request is rejected with a validation error before any VBoxManage call is made.
3. **Given** a user submitting RAM, **When** the value is outside 512–16384 MB, **Then** the request is rejected with a validation error before any VBoxManage call is made.
4. **Given** a user submitting a name, **When** that name is already registered in VirtualBox, **Then** the request is rejected with a clear conflict error and no duplicate DB record is created.
5. **Given** VBoxManage failing during creation, **Then** no DB record is created, the failure is logged, and the user receives an error response with an actionable message.

---

### User Story 2 — Start and Stop a VM (Priority: P1)

An authenticated user (via AI chat command or admin panel) submits a start or stop request for a VM they own. The system validates the current state, executes the VBoxManage command, and updates the status accordingly.

**Why this priority**: Start and stop are the primary operational actions. Without them the VM service has no utility.

**Independent Test**: Can be tested by creating a VM via API, issuing a start request, verifying status moves to "running", issuing a stop request, and verifying status returns to "stopped" — without requiring delete or AI features.

**Acceptance Scenarios**:

1. **Given** a VM in "stopped" status, **When** a start request is received, **Then** the status immediately moves to "starting", VBoxManage `startvm --type headless` is executed, and the status updates to "running" on success.
2. **Given** a VM in "running" status, **When** a stop request is received, **Then** the status immediately moves to "stopping", VBoxManage `controlvm poweroff` is executed, and the status updates to "stopped" on success.
3. **Given** a VM in "starting" or "stopping" status, **When** a start or stop request is received, **Then** HTTP 409 Conflict is returned — no VBoxManage call is made. The admin panel disables action buttons visually for these states.
4. **Given** VBoxManage failing during start or stop, **Then** the VM is set to "error" status, the stderr output is stored in `error_message`, the failure is logged, and an error response is returned.
5. **Given** VBoxManage timing out (> 30 seconds), **Then** the VM is set to "error" status with message "Command timed out", the timeout is logged, and an error response is returned.
6. **Given** a VM in "error" status, **When** a start request is received, **Then** the system treats it as a retry — status moves to "starting" and the start flow begins again.

---

### User Story 3 — Delete a VM (Priority: P2)

An authenticated user (via AI chat command or admin panel) submits a delete request for a VM they own. The VM is unregistered from VirtualBox (disk files deleted) and removed from the database.

**Why this priority**: Delete is needed for cleanup and lifecycle completion, but it is not required to demonstrate core VM control. Create + Start + Stop covers the P1 MVP.

**Independent Test**: Can be tested by stopping a running VM via API, issuing a delete request, confirming the record is removed from the database, and verifying VBoxManage no longer lists it.

**Acceptance Scenarios**:

1. **Given** a VM in "stopped" status, **When** a delete request is received, **Then** VBoxManage `unregistervm --delete` is executed and the DB record is removed on success.
2. **Given** a VM in "running", "starting", or "stopping" status, **When** a delete request is received, **Then** the request is rejected with HTTP 409 — only "stopped" or "error" VMs can be deleted.
3. **Given** VBoxManage failing during deletion, **Then** the DB record is NOT removed, the failure is logged with error details, and an error response is returned.
4. **Given** a user who knows the UUID of another user's VM, **When** they attempt to delete it via the API, **Then** the request returns 404 — no existence is leaked and no action is taken.

---

### User Story 4 — Admin VM List and Status (Priority: P1)

An admin can see all users' VMs at `/admin/vms` with name, OS, RAM, owner, and current status. Status badges are color-coded to communicate health at a glance. Regular users see their VM status exclusively through the AI chat interface.

**Why this priority**: The admin VM list is the primary operational oversight surface. Admins need visibility across all VMs to manage the system.

**Independent Test**: Can be tested by creating VMs via the API and verifying the `/admin/vms` page renders each with correct status badges — no start/stop/delete required.

**Acceptance Scenarios**:

1. **Given** an admin with no VMs in the system, **When** they visit `/admin/vms`, **Then** an empty state message is shown.
2. **Given** an admin visiting `/admin/vms`, **When** there are VMs from multiple users, **Then** all VMs are shown with name, OS, RAM, owner, and a color-coded status badge.
3. **Given** a non-admin user, **When** they navigate to `/admin/vms`, **Then** they are redirected to `/ai` (existing admin guard — unchanged).
4. **Given** a VM whose status changed (e.g., from starting to running), **When** the admin refreshes or triggers an action, **Then** the updated status is reflected.

---

### Edge Cases

- **VBoxManage not installed**: `GET /api/v1/health` detects and reports this. VM create/start/stop/delete return `503 Service Unavailable` with message "VBoxManage not reachable" — no silent failures.
- **Concurrent start on same VM**: The second request finds the VM already in "starting" state and returns HTTP 409 Conflict immediately — no duplicate VBoxManage calls.
- **VM stuck in "starting" or "stopping"**: If VBoxManage exits unexpectedly without updating the DB, the VM remains indefinitely locked in a transitional state. Regular users cannot recover — they receive a 409 on any action. An admin must use the "force reset to stopped" action on `/admin/vms` to clear the state. No self-heal background job for MVP.
- **VM name with special characters**: Names are validated at the API boundary (alphanumeric, hyphens, spaces only). The validated name is passed as a list argument to subprocess — no shell interpolation occurs.
- **VBoxManage succeeds but DB write fails**: The VM exists in VirtualBox but the status update is lost. The VM stays in its previous DB state. The mismatch is logged. A future `showvminfo` call can reconcile.
- **User deletes their account while a VM is running**: Cascade DELETE on the `vms` table removes all DB records. The VirtualBox VM continues running on the host until the admin manually cleans it up — this is a known limitation for single-tenant MVP.
- **RAM at boundary values (512, 16384)**: Both are valid. 511 and 16385 are rejected by the API validator and the DB CHECK constraint as a second line of defense.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow authenticated users to create a VM by specifying a name (1–50 characters, alphanumeric + hyphens + spaces only), an operating system label (free text, required), and RAM in MB (integer, 512–16384 inclusive). Creation is rejected with HTTP 409 when the user already owns `VM_QUOTA_PER_USER` VMs (default: 5, configurable via env var). Quota is enforced before any VBoxManage call.
- **FR-002**: System MUST register the VM in VirtualBox via `VBoxManage createvm --name <name> --register` on creation. If VBoxManage fails, no DB record is created.
- **FR-003**: System MUST store the VM record in the database with `status = 'stopped'` after successful VBoxManage registration.
- **FR-004**: System MUST reject VM creation when the name already exists in VirtualBox, returning HTTP 409 with message "A VM with this name already exists".
- **FR-005**: System MUST allow authenticated users to start a VM whose status is "stopped" or "error". The status MUST be set to "starting" in the database before the VBoxManage call is made.
- **FR-006**: System MUST execute `VBoxManage startvm <name> --type headless` when starting a VM. On success, set status to "running". On failure, set status to "error" and store stderr in `error_message`.
- **FR-007**: System MUST allow authenticated users to stop a VM whose status is "running". The status MUST be set to "stopping" in the database before the VBoxManage call is made.
- **FR-008**: System MUST execute `VBoxManage controlvm <name> poweroff` when stopping a VM. On success, set status to "stopped". On failure, set status to "error" and store stderr in `error_message`.
- **FR-009**: System MUST reject start/stop actions on VMs in "starting" or "stopping" states with HTTP 409 Conflict.
- **FR-010**: System MUST allow authenticated users to delete a VM only when its status is "stopped" OR "error". Deletion requests on any other status ("running", "starting", "stopping") MUST be rejected with HTTP 409.
- **FR-011**: System MUST execute `VBoxManage unregistervm <name> --delete` on deletion. The DB record MUST be removed only after VBoxManage succeeds. On VBoxManage failure, the DB record is preserved and an error is returned.
- **FR-012**: System MUST allow authenticated users to list all their own VMs, returning name, OS, RAM, status, error_message, created_at, and updated_at for each.
- **FR-013**: System MUST enforce a 30-second timeout on every VBoxManage subprocess call. On timeout, set the VM to "error" status with `error_message = "Command timed out"`.
- **FR-014**: System MUST log every VM action (create, start, stop, delete) to the `logs` table before returning the HTTP response — including on failure.
- **FR-015**: System MUST enforce that each user can only read, modify, and delete their own VM records. Requests targeting another user's VM MUST return HTTP 404.
- **FR-016**: System MUST validate VM name at the API boundary: 1–50 characters, alphanumeric, hyphens, and spaces only. Names failing this rule are rejected before any VBoxManage call.
- **FR-017**: System MUST only invoke five whitelisted VBoxManage subcommands: `createvm`, `startvm`, `controlvm`, `unregistervm`, `showvminfo`. No other subcommands are permitted.
- **FR-018**: The **admin panel** MUST display the VM list (all users' VMs) with color-coded status badges: green (running), grey (stopped), amber (starting/stopping), red (error). This page does NOT exist for regular users — they interact via the AI chat only.
- **FR-019**: The **admin panel** VM list MUST disable action buttons (Start, Stop, Delete) when a VM is in "starting" or "stopping" state.
- **FR-020**: The **admin panel** VM list MUST display `error_message` when a VM is in "error" state. For regular users, the AI assistant MUST relay the exact `error_message` content when describing a VM's error state — `error_message` is included in the AI's VM list context so it can surface actionable failure details conversationally.
- **FR-021**: Admin users MUST be able to start, stop, and delete any user's VM from `/admin/vms`. Admin actions bypass the ownership check (FR-015) but still enforce all state-transition rules (FR-005, FR-007, FR-010) and logging (FR-014).
- **FR-022**: Admin users MUST be able to "force reset" any VM to `"stopped"` status from `/admin/vms`, regardless of current state (including "starting", "stopping", or "error"). This action bypasses all state-transition guards, clears `error_message`, logs the action, and does NOT call VBoxManage (it is a DB-only status correction). It is not available to regular users.

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
- Single-tenant deployment: one VirtualBox host. Per-user VM quota defaults to 5, configurable via `VM_QUOTA_PER_USER` environment variable.
- VM creation configures **name and RAM only**. Disk storage, network adapters, and display configuration are out of scope for MVP. The VM is registered and can be started/stopped, but it will not be a fully configured guest OS until those are set up externally. The AI assistant MUST append a post-create note informing the user they need to attach a boot disk via VirtualBox Manager before the VM can run a guest OS.
- VM names must be unique across VirtualBox (not just per user), because VBoxManage enforces global uniqueness. The API reflects this by rejecting duplicate names with 409.
- The `os` field is a free-text label (e.g., "Ubuntu 22.04"). It is not validated against VirtualBox's guest OS type list for MVP.
- "Delete" is destructive: `--delete` removes the VM's disk files from the host. There is no soft delete or recycle bin.
- Status synchronization with VirtualBox is not real-time. The DB is the authoritative source of truth for status. `showvminfo` is only used by the health check and manual reconciliation — not by normal CRUD operations.
- All VBoxManage calls run synchronously within the FastAPI request. No background task queue for MVP.
- The frontend refetches the VM list on every user action (create, start, stop, delete). No real-time polling or WebSocket updates for MVP.

---

## Clarifications

### Session 2026-04-20

- Q: When a VM gets stuck in "starting"/"stopping" with no recovery path, how should it be resolved? → A: Admin-only "force reset to stopped" button on /admin/vms (FR-022 added; no self-heal background job for MVP).
- Q: Can a VM in "error" state be deleted directly, or must the user start it first? → A: Delete is allowed on "error" status VMs directly (FR-010 extended to "stopped" OR "error"; vm_service.py and AI system prompt updated).
- Q: Should the AI relay the exact error_message to regular users when a VM is in error state? → A: Yes — error_message included in AI VM list context so it can surface exact failure details conversationally (FR-020 updated; _build_system_prompt updated).
- Q: Should there be a per-user VM quota to prevent resource exhaustion? → A: Yes — soft limit of 5 VMs per user, configurable via VM_QUOTA_PER_USER env var (FR-001 updated; config.py and vm_service.py updated).
- Q: Should users be warned that newly created VMs have no boot disk and can't run a guest OS? → A: Yes — AI appends a post-create note directing users to attach a boot disk via VirtualBox Manager (Assumptions updated; _execute_action updated).
- Q: Should users be warned that newly created VMs have no boot disk and can't run a guest OS? → A: Yes — AI appends a post-create note directing users to attach a boot disk via VirtualBox Manager (Assumptions updated; _execute_action updated).

### Session 2026-04-09

- Q: Does the admin panel include a VM management page showing all users' VMs? → A: Yes — admin panel has a full VM list page with status badges and controls (FR-018–020 scoped to admin only; regular users have no /vms page).
- Q: What route serves the admin VM management page? → A: `/admin/vms` — consistent with `/admin/*` namespace; User Story 4 updated.
- Q: Should User Stories 1–3 be reframed as backend behavior (API-triggered, source-agnostic)? → A: Yes — stories describe backend behavior triggered by any API caller (AI assistant or admin panel); UI framing removed.
- Q: Should the overview be updated to reflect AI chat (users) + admin panel (admins) access paths? → A: Yes — overview updated; spec 003 referenced for AI chat UX details.
- Q: Should admins have full VM controls (start/stop/delete) on any user's VM from `/admin/vms`? → A: Yes — full controls; bypasses ownership check but enforces all state-transition rules and logging (FR-021 added).

### Session 2026-04-06

- Q: Should VM creation configure disk, network, and display? → A: No. MVP creates and registers the VM with a name and RAM only. All other hardware configuration is out of scope for this spec.
- Q: Should start/stop/delete be synchronous or asynchronous? → A: Synchronous for MVP. VBoxManage calls happen within the request with a 30-second timeout.
- Q: What `--type` should be used for `startvm`? → A: `headless` — no display window required.
- Q: Should duplicate VM names be rejected? → A: Yes — VBoxManage enforces global uniqueness. The API should detect this and return 409 with a clear message.
- Q: Should the frontend poll for live status updates? → A: No polling for MVP. The frontend refetches after each user action.
- Q: What happens to a VM in "error" state — can the user retry start? → A: Yes. "error" → "starting" is a valid transition for retry. The error_message is cleared on the next successful start.
