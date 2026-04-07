# Feature Specification: AI Command Processing

**Feature Branch**: `003-ai-command-processing`  
**Created**: 2026-04-07  
**Status**: Complete  
**Input**: `docs/implementation-plan.md` — "AI" vertical slice  
**Depends on**: `002-vm-management` (VM CRUD service layer — must be complete)

---

## Overview

This spec adds a natural language interface to myVMS. Users can type plain-English commands ("create an Ubuntu VM with 4GB RAM", "stop my test VM") and the system will interpret the command, validate it, and execute the corresponding VM action — all through a conversational chat UI.

The pipeline: user prompt → Groq LLM (JSON-only output) → Pydantic validator → existing VM service → audit log. The AI never executes actions directly; every AI-generated instruction passes through the same validation and execution layer as manual API calls.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Natural Language VM Creation (Priority: P1)

A user types "create an Ubuntu VM with 4GB RAM and call it ubuntu-test" into the AI chat. The system interprets the command, creates the VM, and confirms the result in the chat.

**Why this priority**: AI-driven creation is the primary showcase of the feature. It must work before other AI actions are useful.

**Independent Test**: Can be tested by submitting a plain-English create command and verifying the VM appears on `/vms` and in the `ai_usage` log — without testing start/stop/delete via AI.

**Acceptance Scenarios**:

1. **Given** a logged-in user on `/ai`, **When** they type a valid create command, **Then** the AI returns structured JSON, a VM is created, and the chat shows a confirmation message.
2. **Given** a user typing a command with RAM outside 512–16384, **When** the AI generates parameters with invalid RAM, **Then** the action is rejected at the validation layer and the user sees an error message — no VM is created.
3. **Given** a user typing a command with a name that already exists in VirtualBox, **When** the AI attempts creation, **Then** a 409 conflict from the VM service is surfaced to the user in the chat.
4. **Given** a user typing a completely unrelated message ("what is the weather?"), **When** the AI responds with an error action, **Then** the chat displays a helpful "could not understand" message — no VM action is attempted.

---

### User Story 2 — Natural Language VM Control (Priority: P1)

A user types "start my ubuntu-test VM" or "stop ubuntu-test". The system resolves the name to a UUID using the user's current VM list and executes the action.

**Why this priority**: Start and stop via AI is the core utility of the feature — without it the AI can only create VMs.

**Independent Test**: Can be tested by creating a VM manually, then issuing start/stop commands via AI and verifying status changes.

**Acceptance Scenarios**:

1. **Given** a stopped VM named "ubuntu-test", **When** the user types "start ubuntu-test", **Then** the AI includes the correct VM UUID in its response and the VM is started.
2. **Given** a running VM, **When** the user types "stop my VM", **Then** the VM is stopped and the chat confirms it.
3. **Given** a VM in "starting" or "stopping" state, **When** the user tries to start/stop it via AI, **Then** the 409 from the VM service is surfaced in the chat — the AI does not retry.
4. **Given** no VMs exist, **When** the user types "start my VM", **Then** the AI's empty VM list context causes it to respond with an error action — no action attempted.

---

### User Story 3 — Natural Language VM Deletion (Priority: P2)

A user types "delete my test VM". The system resolves the name, verifies it is stopped, and deletes it.

**Why this priority**: Deletion via AI is useful but not critical to demonstrate the AI feature. Create + Start + Stop covers the P1 showcase.

**Independent Test**: Can be tested by stopping a VM, then typing a delete command via AI and verifying it disappears from `/vms`.

**Acceptance Scenarios**:

1. **Given** a stopped VM, **When** the user types "delete my test VM", **Then** the VM is deleted and the chat confirms it.
2. **Given** a running VM, **When** the user types "delete it", **Then** the 409 from the VM service ("stop it first") is surfaced in the chat.

---

### User Story 4 — Rate Limiting (Priority: P2)

A user cannot send more than 10 AI commands per minute, preventing abuse of the Groq API.

**Acceptance Scenarios**:

1. **Given** a user sending 10 commands within 60 seconds, **When** they send an 11th, **Then** they receive a clear rate-limit message in the chat and no Groq API call is made.
2. **Given** a user who hit the limit and waits 60 seconds, **When** they send another command, **Then** it succeeds normally.

---

### Edge Cases

- **Groq returns non-JSON**: The validator catches `JSONDecodeError` and returns a 400 with a user-friendly message. No VM action is attempted.
- **Groq returns unknown action** (e.g., `"reboot_vm"`): The validator rejects the action — it is not in the whitelist. No VM action is attempted.
- **Groq API unavailable**: Returns 503 "AI service unavailable" — not a VM error.
- **AI generates an invalid VM name** (special chars, too long): The Pydantic validator catches this before any VM service call.
- **User has many VMs**: The VM list injected into the system prompt is JSON-serialized in full. For MVP (single-tenant, small VM counts), this is acceptable. The 500-char prompt limit prevents abuse.
- **Ambiguous reference** ("start my VM" with multiple VMs): The LLM uses the status field in the VM list context to pick the most appropriate VM. If it guesses wrong, the user can be more specific.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST accept a natural language prompt (1–500 characters) from an authenticated user and return a structured result.
- **FR-002**: System MUST call the Groq API with a system prompt that includes the user's current VM list, forcing JSON-only output.
- **FR-003**: System MUST validate the Groq response against per-action Pydantic schemas before executing any VM action. Non-JSON responses MUST be rejected with HTTP 400.
- **FR-004**: System MUST support exactly four AI-executable actions: `create_vm`, `start_vm`, `stop_vm`, `delete_vm`. Any other action in the AI response MUST be rejected.
- **FR-005**: System MUST execute the validated action by calling the existing VM service functions — no separate execution path for AI-originated actions.
- **FR-006**: System MUST log every AI command to the `ai_usage` table (prompt, raw response, token count) before returning the HTTP response.
- **FR-007**: System MUST log every AI command to the `logs` table with `action = 'ai_command'` (success or failure) before returning the HTTP response.
- **FR-008**: System MUST enforce a rate limit of 10 AI commands per minute per user. Requests exceeding this MUST return HTTP 429.
- **FR-009**: System MUST surface VM service errors (404, 409, 500, 503) to the frontend with their original status codes — not mask them.
- **FR-010**: System MUST include the user's current VM list (id, name, status, os, ram) in the Groq system prompt so the AI can resolve VM references to UUIDs.
- **FR-011**: Frontend MUST display a scrollable message history of user prompts and AI responses within the current session.
- **FR-012**: Frontend MUST show a loading indicator while awaiting the AI response.
- **FR-013**: Frontend MUST enforce the 500-character prompt limit in the input field with a visible character counter.
- **FR-014**: Frontend MUST display error messages (from rate limit, validation, VM service, Groq outage) clearly in the chat.
- **FR-015**: The AI page MUST require authentication. Unauthenticated users MUST be redirected to `/login`.

### Key Entities

- **AI Command**: A user-submitted natural language prompt that is interpreted by the Groq LLM into a structured VM action. A command is either executed (producing a VM state change) or rejected (validation failure, unknown action, Groq error). Every command produces a record in both `ai_usage` and `logs`.
- **AI Response**: The raw JSON string returned by Groq. Contains an `action` field and action-specific parameters. Must pass validation before execution. Stored verbatim in `ai_usage.response`.
- **AI Usage Record**: Persisted to the `ai_usage` table. Tracks prompt text, raw AI response, token count, and user. Used for analytics and cost tracking.

---

## Success Criteria *(mandatory)*

- **SC-001**: A user can type "create an Ubuntu VM with 2GB RAM" and a VM appears in the database with the correct parameters.
- **SC-002**: Every AI command (successful or failed) produces a record in `ai_usage` with the correct prompt, response, and token count — 0 unlogged commands.
- **SC-003**: Every AI command produces a record in `logs` with `action = 'ai_command'` and the correct status — 0 unlogged commands.
- **SC-004**: Non-JSON and unknown-action AI responses are rejected before reaching the VM service — 0 invalid commands executed.
- **SC-005**: The 11th AI command within 60 seconds returns HTTP 429 without calling Groq — 0 rate-limit bypasses.
- **SC-006**: `pytest backend/tests/test_ai_service.py` passes all 13 test cases with mocked Groq API.
- **SC-007**: VM service errors (409, 404, 503) from AI-triggered actions are surfaced with their original status codes — 0 masked errors.
- **SC-008**: The AI page at `/ai` redirects unauthenticated users to `/login` — 0 unauthenticated AI requests.

---

## Assumptions

- The Groq API is available and the `GROQ_API_KEY` environment variable is set. The `groq` Python SDK is already in `requirements.txt`.
- The `ai_usage` table and its RLS policies already exist (created in `supabase/migrations/001_initial_schema.sql` as part of spec 001).
- `LogAction.ai_command` is already defined in `backend/app/models/enums.py` (spec 001).
- The model `llama-3.3-70b-versatile` is used for all AI commands. Model selection is not configurable at runtime for MVP.
- Rate limiting is in-memory (per-process). A server restart resets all rate limit windows. Acceptable for single-tenant MVP.
- The AI has no persistent conversation memory. Each command is processed independently. The LLM receives only the current system prompt and the single user message — no history.
- No streaming output. The entire Groq response is received before the frontend is updated.
- Token cost tracking is informational only. No hard limits on token spend per user for MVP.

---

## Clarifications

### Session 2026-04-07

- Q: Should AI conversation history be sent to Groq for multi-turn interactions? → A: No. Single-turn only for MVP. YAGNI.
- Q: Should the rate limiter use Redis or a database? → A: In-memory dict. Single-tenant MVP doesn't need distributed state.
- Q: Should AI actions go through a different execution path than manual API calls? → A: No. AI-validated actions call the same vm_service functions as the direct endpoints.
- Q: Should AI responses be streamed to the frontend? → A: No streaming for MVP. Full response returned after Groq completes.
- Q: Should there be a `GET /api/v1/ai/history` endpoint? → A: Deferred. History is in `ai_usage` table but no route exposes it for MVP.
