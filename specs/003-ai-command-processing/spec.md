# Feature Specification: AI Command Processing

**Feature Branch**: `003-ai-command-processing`  
**Created**: 2026-04-07  
**Status**: Complete (amended 2026-04-15 — free conversation mode)  
**Input**: `docs/implementation-plan.md` — "AI" vertical slice  
**Depends on**: `002-vm-management` (VM CRUD service layer — must be complete)

---

## Overview

This spec adds a natural language interface to myVMS. Users can type commands in any language ("create an Ubuntu VM with 4GB RAM", "arrête ma VM test", "أنشئ VM بذاكرة 4 جيجا") and the system will interpret the command, validate it, and execute the corresponding VM action — all through a conversational chat UI. The AI MUST respond in the same language the user typed in — no language restriction.

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

### User Story 4 — Free Conversation (Priority: P2)

A user types "what is the difference between Ubuntu and Debian?" or "which OS should I pick for a dev VM?" The AI responds in natural language — no VM action is taken.

**Why this priority**: Without this, the AI is frustrating to use: any off-topic message returns an error. Users expect to be able to ask questions naturally, the same way they would talk to any AI assistant.

**Independent Test**: Can be tested by typing a general question in the chat and verifying the response is a conversational answer (not an error), no VM is created/modified, and the exchange is logged to `ai_usage`.

**Acceptance Scenarios**:

1. **Given** a logged-in user on `/ai`, **When** they type "what is Ubuntu?", **Then** the AI responds with a helpful explanation and no VM action is taken.
2. **Given** a user asking a general question, **When** the AI returns a `chat` response, **Then** the frontend displays the message without an action badge or error styling.
3. **Given** a user asking "how many VMs can I create?", **When** the message is not a direct VM command, **Then** the AI may answer with a `chat` response or trigger `query_analytics` — either is acceptable; no error is returned.
4. **Given** a user typing a genuinely ambiguous or harmful request, **When** the AI cannot respond helpfully, **Then** the AI returns an `error` action (HTTP 400) — the `chat` action is not a blanket catch-all for adversarial input.

---

### User Story 5 — Rate Limiting (Priority: P2)

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
- **User has many VMs**: The VM list injected into the system prompt is JSON-serialized in full. For MVP (single-tenant, small VM counts), this is acceptable. The 2000-char prompt limit is generous enough for complex descriptions while still bounding abuse.
- **Ambiguous reference** ("start my VM", "stoppe celle qui tourne pour rien"): The LLM uses all available VM context (name, os, status, ram) to pick the most appropriate target and acts immediately. The confirmation message names the VM that was acted on. If the AI guesses wrong, the user corrects in the next message — no pre-action clarification prompt is shown.
- **`chat` message too long**: If the LLM generates a `message` field exceeding 2000 characters, the `AIChat` Pydantic validator rejects it as a malformed response (HTTP 400) — same treatment as any other parameter violation.
- **User asks a VM question via `chat`** (LLM uses `chat` when `start_vm` was more appropriate): The user sees a text response instead of an executed action. They can rephrase to trigger the correct action. No harm done; no VM state changed.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST accept a natural language prompt (1–2000 characters) in any language from an authenticated user and return a structured result. The AI response MUST be in the same language the user typed in — no language restriction. The AI MUST infer intent and act accordingly:
  - **Described need** ("j'ai un projet python avec beaucoup de données") → infer name, OS, RAM and execute `create_vm` immediately.
  - **Config question** ("c'est quoi la meilleure config pour analyser 50GB de CSV?") → infer optimal parameters and execute `create_vm` directly — no text-only answer.
  - **Ambiguous VM reference** ("stoppe celle qui tourne pour rien") → pick the most likely VM from context and execute the action; name it in the confirmation.
  - **General conversation** ("can I talk to you in English?", "what is Ubuntu?") → respond via `chat` action with a natural language reply; no VM action taken.
- **FR-002**: System MUST call the Groq API with a system prompt that includes the user's current VM list, forcing JSON-only output. When the AI infers a `create_vm` action from context, it MUST act immediately and return a confirmation message — no user confirmation step is required before execution.
- **FR-003**: System MUST validate the Groq response against per-action Pydantic schemas before executing any VM action. Non-JSON responses MUST be rejected with HTTP 400.
- **FR-004**: System MUST support exactly six AI actions: `create_vm`, `start_vm`, `stop_vm`, `delete_vm`, `query_analytics`, `chat`. Any other action in the AI response MUST be rejected. The `error` action is additionally reserved for AI-signalled unresolvable requests (returns HTTP 400). Per-action Pydantic schemas:
  - `create_vm`: `{ action: "create_vm", name: str (1-50 chars), os: str, ram: int (512-16384) }`
  - `start_vm`: `{ action: "start_vm", vm_id: str (UUID) }`
  - `stop_vm`: `{ action: "stop_vm", vm_id: str (UUID) }`
  - `delete_vm`: `{ action: "delete_vm", vm_id: str (UUID) }`
  - `query_analytics`: `{ action: "query_analytics", message: str (1-2000 chars) }` — the AI includes a natural language summary of the analytics data in `message`. No VM service call is made; the backend calls the appropriate analytics endpoint (`/api/v1/analytics` or `/api/v1/analytics/admin` based on user role) and returns the AI's summary as the `result`.
  - `chat`: `{ action: "chat", message: str (1-2000 chars) }` — general conversation, no VM or analytics action.
- **FR-005**: System MUST execute the validated action by calling the existing VM service functions — no separate execution path for AI-originated actions.
- **FR-006**: System MUST log every AI command to the `ai_usage` table (prompt, raw response, token count) before returning the HTTP response.
- **FR-007**: System MUST log every AI command to the `logs` table with `action = 'ai_command'` (success or failure) before returning the HTTP response.
- **FR-008**: System MUST enforce a rate limit of 10 AI commands per minute per user. Requests exceeding this MUST return HTTP 429.
- **FR-009**: System MUST surface VM service errors (404, 409, 500, 503) to the frontend with their original status codes — not mask them.
- **FR-010**: System MUST include the user's current VM list (id, name, status, os, ram) in the Groq system prompt so the AI can resolve VM references to UUIDs.
- **FR-011**: Frontend MUST display a scrollable message history of user prompts and AI responses within the current session.
- **FR-012**: Frontend MUST show a loading indicator while awaiting the AI response.
- **FR-013**: Frontend MUST enforce the 2000-character prompt limit in the input field with a visible character counter.
- **FR-014**: Frontend MUST display error messages (from rate limit, validation, VM service, Groq outage) clearly in the chat.
- **FR-014a**: Frontend MUST render VM status keywords (`Running`, `Stopped`, `Error`) as color-coded badges wherever they appear in AI chat responses — green for Running, orange for Stopped, red for Error. Detection is client-side only; backend response format is unchanged.
- **FR-015**: The AI page MUST require authentication. Unauthenticated users MUST be redirected to `/login`.
- **FR-016**: `/ai` is the primary post-login landing page for regular users. After successful login, users MUST be redirected to `/ai` — not `/dashboard`. The `/dashboard` route is removed for regular users.
- **FR-017**: On every session start, the frontend MUST call `GET /api/v1/analytics` automatically and display the result as the AI's opening message (e.g., "You have 3 VMs — 2 running, 1 stopped. What would you like to do?"). This replaces the removed dashboard stat cards. If the analytics call fails, the greeting MUST fall back to a generic welcome message — no crash.
- **FR-019**: System MUST support a `chat` action for general conversation. When the AI determines the user's intent is not a VM action and not an analytics query, it MUST return `{"action": "chat", "message": "<response text>"}`. The backend MUST validate this against the `AIChat` Pydantic schema (`message: str, 1–2000 chars`) and return the message as the `result` field of `AICommandResponse` with HTTP 200. No VM service call is made for `chat` actions. The AI MUST respond in the user's language (same rule as all other actions). The `chat` action is subject to rate limiting, dual logging, and all other existing pipeline rules.

- **FR-018**: The AI MUST answer on-demand analytics questions mid-conversation by calling the appropriate endpoint based on the user's role:
  - **Regular user**: `GET /api/v1/analytics` for personal VM counts (e.g., "how many VMs do I have?", "كم عدد VMs؟").
  - **Admin user**: `GET /api/v1/analytics` for personal questions; `GET /api/v1/analytics/admin` for system-wide questions (e.g., "how many total users?", "how many VMs are running across all users?").
  All responses MUST be in the user's language. Failure MUST be acknowledged gracefully in natural language.

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
- The model **`llama-4-scout`** (Groq) is used for all AI commands. It covers function calling, multilingual input, and text generation — the three requirements for myVMS. Model selection is not configurable at runtime for MVP.
- Rate limiting is in-memory (per-process). A server restart resets all rate limit windows. Acceptable for single-tenant MVP.
- The AI has no persistent conversation memory. Each command is processed independently. The LLM receives only the current system prompt and the single user message — no history.
- No streaming output. The entire Groq response is received before the frontend is updated.
- Token cost tracking is informational only. No hard limits on token spend per user for MVP.

---

## Clarifications

### Session 2026-04-07

- Q: Should AI conversation history be sent to Groq for multi-turn interactions? → A: No. Single-turn only for MVP. YAGNI.

### Session 2026-04-09

- Q: Which Groq model should be used for all AI operations? → A: `llama-4-scout` — covers function calling, multilingual, and text generation. Replaces `llama-3.3-70b-versatile` (no function calling) and `llama3-groq-70b-8192-tool-use-preview` (not in current Groq catalog). Applied across specs 003 and 004.
- Q: Should `/ai` become the primary post-login landing page, replacing `/dashboard`? → A: Yes — users land on `/ai` after login; `/dashboard` is removed for regular users (FR-016 added; spec 001 auth redirect needs update).
- Q: Should the AI greet the user with a VM summary on every session start by calling the analytics endpoint? → A: Yes — frontend auto-calls `GET /api/v1/analytics` on open and displays result as opening message; fallback to generic greeting on failure (FR-017 added).
- Q: Should the spec require all-language support and remove "plain-English" framing? → A: Yes — AI MUST respond in user's input language; "plain-English" removed from overview; FR-001 updated to require multilingual responses.
- Q: Should the AI answer on-demand analytics questions mid-conversation by calling `GET /api/v1/analytics`? → A: Yes — AI calls analytics endpoint on-demand when user asks about VM counts; responds in user's language; graceful failure in natural language (FR-018 added).
- Q: Should the rate limiter use Redis or a database? → A: In-memory dict. Single-tenant MVP doesn't need distributed state.
- Q: Should AI actions go through a different execution path than manual API calls? → A: No. AI-validated actions call the same vm_service functions as the direct endpoints.
- Q: Should AI responses be streamed to the frontend? → A: No streaming for MVP. Full response returned after Groq completes.
- Q: Should there be a `GET /api/v1/ai/history` endpoint? → A: Deferred. History is in `ai_usage` table but no route exposes it for MVP.

### Session 2026-04-15

- Q: Which scope of PDF "VM Automation Chatbot" behaviors applies to this modification? → A: Option B — free conversation + intent-based VM creation. The AI infers VM name, OS, and RAM from the user's description (e.g. "j'ai un projet python avec beaucoup de données" → appropriate name/os/ram). No schema changes (no vm_type, cpu, packages columns). Schema extension is deferred to a future spec.
- Q: When AI infers a VM config from user intent, should it confirm before acting or act immediately? → A: Act immediately and confirm after — AI creates the VM and returns a confirmation message showing what was decided. No round-trip confirmation step.
- Q: When a user references a VM ambiguously (no explicit name), should the AI pick and act or ask for clarification? → A: AI picks the most likely VM using context (status, name, os from VM list) and acts immediately. The confirmation message names the VM that was acted on so the user can verify.
- Q: When a user asks a configuration question ("c'est quoi la meilleure config pour analyser 50GB de CSV?"), should the AI answer in text or create the VM directly? → A: Create the VM directly with optimal inferred parameters. Config questions imply creation intent — the AI acts as a doer, not just an advisor.
- Q: Should the prompt length limit be raised to support free-form conversation and complex project descriptions? → A: Raise to 2000 characters — covers long project descriptions and detailed conversational context.

### Session 2026-04-15 (UI prototype review)

- Q: Should the AI chat be a floating widget or a full-screen page at `/ai`? → A: Full-screen page — `/ai` remains a dedicated route. The prototype visual style (dark card, green accents, color-coded VM status) is applied as styling only. No floating/minimize/close widget behavior.
- Q: Is the "Choose Your Role" landing screen a real auth flow change or visual redesign? → A: Visual redesign only — both User/Admin cards lead to the same Supabase login form. Role is determined by `is_admin` in the JWT post-login. No spec 001 changes required.
- Q: Should VM status words in chat responses be color-coded? → A: Yes — frontend detects `Running`/`Stopped`/`Error` keywords in AI response text and renders them as color-coded badges (green/orange/red). Backend `result` string stays plain text; no backend changes.
- Q: Should the dark green prototype theme apply globally or only to specific pages? → A: Global — dark background + green accent applied to all pages via `globals.css` and root `layout.tsx`. All routes inherit the theme.
