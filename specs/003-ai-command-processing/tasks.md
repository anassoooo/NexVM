# Tasks: AI Command Processing

**Feature**: AI Command Processing
**Branch**: `003-ai-command-processing`
**Depends on**: `002-vm-management` (VM CRUD service — must be complete)
**Tests**: Backend unit tests for `ai_service.py` with mocked Groq SDK (23+ cases)

## Format: `- [ ] T### [P?] [US?] Description with file path`

- **[P]**: Can run in parallel (different files, no shared dependencies)
- **[US#]**: Primary user story served

---

## Phase 1: Setup

**Purpose**: Prepare the feature branch and verify all prerequisites from `002-vm-management`.

- [ ] T001 Create branch `003-ai-command-processing` from main; verify `groq` SDK in `backend/requirements.txt`; verify `002-vm-management` is complete — confirm `vm_service.create_vm`, `vm_service.start_vm`, `vm_service.stop_vm`, `vm_service.delete_vm`, `vm_service.list_vms` all exist and pass; verify `ai_usage` table and `LogAction.ai_command` enum exist from spec 001

**Checkpoint**: `cd backend && python -c "from app.services.vm_service import create_vm, start_vm, stop_vm, delete_vm, list_vms"` succeeds.

---

## Phase 2: Foundational — Schemas, Service & Route

**Purpose**: Build the complete backend pipeline — Pydantic schemas for all 6 AI actions, the AI service with Groq integration, rate limiting, validation, execution, and dual logging, the FastAPI route, and frontend type definitions.

- [ ] T002 Add Pydantic schemas to `backend/app/models/schemas.py`:
  - `AICommandRequest(prompt: str)` — `Field(min_length=1, max_length=2000)`
  - `AICommandResponse(action: str, result: str, ai_response: dict[str, Any])`
  - `AICreateVM(action: Literal["create_vm"], name: str 1-50 chars with regex, os: str, ram: int 512-16384)` — reuse `_VM_NAME_RE` regex and `validate_name` from `VMCreate`
  - `AIStartVM(action: Literal["start_vm"], vm_id: uuid.UUID)`
  - `AIStopVM(action: Literal["stop_vm"], vm_id: uuid.UUID)`
  - `AIDeleteVM(action: Literal["delete_vm"], vm_id: uuid.UUID)`
  - `AIQueryAnalytics(action: Literal["query_analytics"], scope: Literal["user", "admin"] = "user")`
  - `AIChat(action: Literal["chat"], message: str)` — `Field(min_length=1, max_length=2000)`

- [ ] T003 Create `backend/app/services/ai_service.py` with the following components:
  - **Constants**: `GROQ_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"`, `ALLOWED_ACTIONS` set with all 6 actions, `ACTION_SCHEMAS` dict mapping action names to Pydantic classes, `max_tokens=512`, `RATE_LIMIT_MAX=10`, `RATE_LIMIT_WINDOW=60`
  - **`SYSTEM_PROMPT`**: template with `{vm_list_json}` placeholder, JSON-only output constraint, all 6 action schemas documented (initial version — enhanced in T010 for free conversation)
  - **`_check_rate_limit(user_id)`**: in-memory sliding window using `_rate_limit_store: dict[str, list[float]]` with `threading.Lock`; 10 req/60s; raises HTTP 429
  - **`_build_system_prompt(user_id)`**: calls `vm_service.list_vms(user_id)`, serializes `[{id, name, status, os, ram}]` into SYSTEM_PROMPT
  - **`_call_groq(system_prompt, user_prompt) -> (raw_text, tokens)`**: creates `Groq` client, calls `chat.completions.create`; catches `APITimeoutError` → 504, `APIError` → 503
  - **`_validate_ai_response(raw_json) -> dict`**: `json.loads` → action whitelist check → `ACTION_SCHEMAS[action].model_validate()` → `model_dump(mode="json")`; rejects non-JSON (400), unknown action (400), error action (400 with AI message), validation errors (400)
  - **`_execute_action(validated, user_id) -> str`**: dispatches `create_vm`/`start_vm`/`stop_vm`/`delete_vm` to `vm_service` functions, `query_analytics` to `analytics_service`, `chat` returns `validated["message"]` directly
  - **`_log_ai_usage(user_id, prompt, response, tokens)`**: inserts to `ai_usage` table; logs failure internally but does not cascade
  - **`_log_action(user_id, target, status, message)`**: inserts to `logs` table with `action=ai_command`; logs failure internally but does not cascade
  - **`process_ai_command(prompt, user_id) -> AICommandResponse`**: orchestrates rate check → build prompt → call Groq → validate → execute → dual log → return; on failure: still logs to both tables, then re-raises

- [ ] T004 Create `backend/app/routes/ai.py`:
  - Single endpoint `POST /command` with `response_model=AICommandResponse`
  - Uses `Depends(get_current_user)` for JWT auth
  - Runs `ai_service.process_ai_command()` in `ThreadPoolExecutor` (sync Groq SDK in async FastAPI)

- [ ] T005 Update `backend/app/main.py`:
  - `app.include_router(ai_router, prefix="/api/v1/ai", tags=["ai"])`

- [ ] T006 [P] Add `AICommandResponse` interface to `frontend/types/index.ts`:
  - `{ action: string; result: string; ai_response: Record<string, unknown> }`

**Checkpoint**: `cd backend && python -c "from app.main import app"` succeeds. `POST /api/v1/ai/command` appears in route list. All 8 schemas importable.

---

## Phase 3: US1 — Natural Language VM Creation (P1)

**Purpose**: Verify the create_vm pipeline end-to-end — AI interprets natural language, generates valid JSON, validator catches bad params, VM is created via existing service, dual logging works.

**Independent test**: Submit "create an Ubuntu VM with 4GB RAM" and verify VM appears in database and `ai_usage` log — without testing start/stop/delete.

- [ ] T007 [US1] Add create_vm test cases to `backend/tests/test_ai_service.py` (mocked Groq, mocked Supabase):
  - **(1) create_vm happy path**: Groq returns `{"action":"create_vm","name":"ubuntu-vm","os":"Ubuntu 22.04","ram":4096}` → VM created → assert `result.action=="create_vm"`, `"Created VM 'ubuntu-vm'"` in result, `vm_service.create_vm` called, `ai_usage` + `logs` inserts called
  - **(2) create_vm invalid RAM**: Groq returns `ram:99999` → validator rejects → HTTP 400
  - **(3) create_vm invalid name (special chars)**: Groq returns `name:"$$bad$$"` → validator rejects → HTTP 400
  - **(4) VM list injected in system prompt**: `vm_service.list_vms` returns `[{name:"my-special-vm",...}]` → assert "my-special-vm" appears in Groq `messages[0].content`

**Checkpoint**: `pytest backend/tests/test_ai_service.py -v` — 4 passed.

---

## Phase 4: US2 — Natural Language VM Control (P1)

**Purpose**: Verify start/stop via AI — name→UUID resolution through VM list in system prompt, VM service errors (409 wrong state) propagate correctly.

**Independent test**: Create a VM manually, then issue start/stop commands via AI and verify status changes.

- [ ] T008 [US2] Add VM control test cases to `backend/tests/test_ai_service.py`:
  - **(5) start_vm happy path**: Groq returns `{"action":"start_vm","vm_id":"<UUID>"}` → VM started → assert `"Started"` in result, `vm_service.start_vm` called with correct UUID
  - **(6) stop_vm happy path**: Groq returns `{"action":"stop_vm","vm_id":"<UUID>"}` → VM stopped → assert `vm_service.stop_vm` called
  - **(7) VM service raises 409 (transitional state)**: Groq returns valid start_vm → `vm_service.start_vm` raises HTTP 409 → assert 409 propagates AND `ai_usage` still logged
  - **(8) Empty VM list context**: `vm_service.list_vms` returns `[]` → AI returns error action → HTTP 400 (no action attempted)

**Checkpoint**: `pytest backend/tests/test_ai_service.py -v` — 8 passed.

---

## Phase 5: US3 — Natural Language VM Deletion (P2)

**Purpose**: Verify delete via AI — stopped VM deleted, running VM rejection surfaced.

**Independent test**: Stop a VM, type delete command via AI, verify it disappears from `/vms`.

- [ ] T009 [US3] Add delete test cases to `backend/tests/test_ai_service.py`:
  - **(9) delete_vm happy path**: Groq returns `{"action":"delete_vm","vm_id":"<UUID>"}` → VM deleted → assert `vm_service.delete_vm` called
  - **(10) delete_vm running VM**: Groq returns valid delete_vm → `vm_service.delete_vm` raises HTTP 409 "stop it first" → assert 409 propagates to caller

**Checkpoint**: `pytest backend/tests/test_ai_service.py -v` — 10 passed.

---

## Phase 6: US4 — Free Conversation (P2)

**Purpose**: Enable free conversation — AI responds conversationally for non-VM questions, infers VM parameters from project descriptions, resolves ambiguous VM references using context. This is the most critical behavioral change: redesign the system prompt to support chat fallback, intent-based creation, config-to-create, and ambiguity resolution.

**Independent test**: Type "what is Ubuntu?" → HTTP 200, `action="chat"`, natural reply, no VM touched, one `ai_usage` record.

- [ ] T010 [US4] Redesign `SYSTEM_PROMPT` in `backend/app/services/ai_service.py` — replace the basic prompt with behavior rules (keep `{vm_list_json}` placeholder and JSON-only output constraint):
  - **`chat` action**: `{"action":"chat","message":"<natural language reply in user's language>"}` — use when user asks a general question, has conversation, or says something unrelated to VM actions
  - **Intent-based creation**: when user describes a need without explicit VM params (e.g. "j'ai un projet python avec beaucoup de données"), infer an appropriate `name` (e.g. `vm-python-project`), `os` (e.g. `Ubuntu`), `ram` (e.g. `4096`) and return `create_vm` — do not ask for clarification
  - **Config question → creation**: when user asks "what's the best config for X?", infer optimal parameters and return `create_vm` directly — do not answer in text
  - **Ambiguous reference resolution**: when user references a VM without naming it (e.g. "stoppe celle qui tourne pour rien", "start the ML one"), use the injected VM list (name, os, status) to pick the most likely target and act; name the chosen VM in the confirmation
  - **`error` action**: reserve only for genuinely harmful or completely unresolvable requests
  - Keep all existing action schemas and formats unchanged
  - Instruct AI to respond in the same language the user typed in

- [ ] T011 [US4] Add free conversation + intent inference test cases to `backend/tests/test_ai_service.py`:
  - **(11) chat happy path**: prompt `"what is Ubuntu?"` → mock returns `{"action":"chat","message":"Ubuntu is a Linux distribution..."}` → HTTP 200, `result=="Ubuntu is a Linux distribution..."`, no `vm_service` called, `ai_usage` logged
  - **(12) chat message too long**: mock returns `{"action":"chat","message":"<2001-char string>"}` → Pydantic rejects → HTTP 400
  - **(13) intent-based creation**: prompt `"I have a Python data science project"` → mock returns `{"action":"create_vm","name":"vm-data-science","os":"Ubuntu","ram":4096}` → VM created, logged to `ai_usage`
  - **(14) config question → creation**: prompt `"best config for 50GB CSV analysis?"` → mock returns `create_vm` with inferred params → VM created
  - **(15) ambiguous stop**: prompt `"stop the running one"`, VM list has `[{name:"vm-web",status:"running"},{name:"vm-ml",status:"stopped"}]` → mock returns `{"action":"stop_vm","vm_id":"<vm-web-uuid>"}` → correct VM stopped
  - **(16) ambiguous reference, no VMs**: prompt `"start the ML one"`, empty VM list → mock returns `{"action":"chat","message":"You don't have any VMs yet."}` → HTTP 200, chat response

**Checkpoint**: `pytest backend/tests/test_ai_service.py -v` — 16 passed. Manual test: `curl -X POST /api/v1/ai/command -d '{"prompt":"what is Ubuntu?"}'` → chat response, HTTP 200.

---

## Phase 7: US5 — Rate Limiting (P2)

**Purpose**: Verify the in-memory sliding window rate limiter and AI pipeline error handling (non-JSON, unknown action, API outage, prompt validation).

**Independent test**: Send 10 commands rapidly, verify 11th returns 429, wait 60s, verify next succeeds.

- [ ] T012 [US5] Add rate limiting + pipeline error test cases to `backend/tests/test_ai_service.py`:
  - **(17) rate limit exceeded**: send 10 valid commands within 60s → 11th raises HTTP 429
  - **(18) Groq returns non-JSON**: Groq returns `"I cannot do that, sorry"` (plain text) → HTTP 400, `ai_usage` logged
  - **(19) Groq returns unknown action**: Groq returns `{"action":"reboot_vm","vm_id":"<UUID>"}` → HTTP 400
  - **(20) Groq API error (503)**: `Groq` client raises `APIError` → HTTP 503
  - **(21) prompt at 2000 chars**: prompt of exactly 2000 chars → accepted (no 422)
  - **(22) prompt at 2001 chars**: prompt of 2001 chars → HTTP 422 validation error before Groq called

**Checkpoint**: `pytest backend/tests/test_ai_service.py -v` — 22 passed.

---

## Phase 8: Frontend Integration

**Purpose**: Build the AI chat page, interactive chat component, analytics greeting, navigation updates, and visual styling.

- [ ] T013 Create `frontend/app/ai/page.tsx` — server component:
  - Auth check via `supabase.auth.getUser()`, redirect to `/login` if unauthenticated
  - Renders `<AIChat />` in a centered container (`max-w-2xl mx-auto`)

- [ ] T014 Create `frontend/components/ai-chat.tsx` — client component:
  - `messages` state: `{id, role, content, action?, error?}[]`
  - Input form: text field (`maxLength={2000}`), character counter showing `{input.length}/2000`, submit button
  - Calls `api.post<AICommandResponse>("/api/v1/ai/command", { prompt })` on submit
  - User messages right-aligned; assistant messages left-aligned; error messages styled in red
  - Action badge on assistant messages showing action name (e.g. "create_vm" pill)
  - "Thinking..." indicator while `loading===true`
  - Submit disabled when loading or input empty
  - Auto-scroll to bottom on new messages

- [ ] T015 [US2] Add analytics greeting `useEffect` on mount to `frontend/components/ai-chat.tsx`:
  - Calls `GET /api/v1/analytics` on session start
  - Displays VM summary as opening message: `"You have N VMs — X running, Y stopped. What would you like to do?"`
  - Falls back to `"Welcome! What would you like to do?"` on analytics call failure — no crash

- [ ] T016 [P] Update `frontend/app/layout.tsx`:
  - Add "AI" nav link pointing to `/ai` after the home link

- [ ] T017 [P] Update `frontend/app/(auth)/login/page.tsx`:
  - Change post-login redirect from `/dashboard` to `/ai` (FR-016)

- [ ] T018 [P] Replace `frontend/app/dashboard/page.tsx` with `redirect("/ai")` (FR-016 — `/dashboard` removed for regular users)

- [ ] T019 [US4] Update `frontend/components/ai-chat.tsx` for chat-specific behavior:
  - Hide action badge when `action === "chat"` (no badge label for conversational replies)
  - Add status keyword badge rendering: parse assistant message `content` for words `Running`, `Stopped`, `Error` (case-sensitive match on word boundaries) and wrap each in a `<span>` with Tailwind color class — `text-green-400 bg-green-400/10` for Running, `text-orange-400 bg-orange-400/10` for Stopped, `text-red-400 bg-red-400/10` for Error

- [ ] T020 Apply dark theme prototype styling to `frontend/components/ai-chat.tsx` and `frontend/app/ai/page.tsx`:
  - User messages: right-aligned green bubbles (`bg-green-600 text-white rounded-2xl rounded-br-sm`)
  - Assistant messages: left-aligned dark cards (`bg-slate-800 text-slate-100 rounded-2xl rounded-bl-sm border border-slate-700`)
  - Input area: dark background (`bg-slate-800`), green send button (`bg-green-600 hover:bg-green-700`)
  - Chat container: centered card on `/ai` page (`max-w-2xl mx-auto h-screen flex flex-col`)
  - Page heading and description updated to remove "plain English" (multilingual support)

**Checkpoint**: `/ai` loads with dark chat UI, redirects unauthenticated users, chat sends commands, displays responses with action badges and status badges, analytics greeting shows on load.

---

## Phase 9: Polish

**Purpose**: Apply global dark theme across all pages, update auth UI, finalize documentation, and verify full test suite.

- [ ] T021 [P] Update `frontend/app/globals.css` and `frontend/app/layout.tsx` for global dark theme:
  - Set CSS variables: dark background (`--background: #0d1117`), green primary accent (`--primary: #10b981`), light foreground (`--foreground: #e2e8f0`)
  - Add dark base classes to `<body>` in `layout.tsx`: `className="bg-[#0d1117] text-slate-100 min-h-screen antialiased"`
  - Ensure all pages (admin, vms, ai) inherit the dark background

- [ ] T022 [P] Redesign `frontend/app/(auth)/login/page.tsx` with two-card role-selection UI:
  - "User" card (person icon, "Login as User" button) and "Admin" card (shield icon, "Login as Admin" button)
  - Clicking either card reveals the same email+password fields for Supabase `signInWithPassword`
  - Apply dark green prototype styling (dark card backgrounds, green accent buttons)
  - Do NOT change the underlying auth logic — role is determined by `is_admin` in JWT post-login
  - Update `frontend/app/(auth)/signup/page.tsx` with matching dark styling for visual consistency

- [ ] T023 [P] Update `specs/003-ai-command-processing/quickstart.md` with smoke tests for:
  - Free conversation — "what is Ubuntu?" → chat reply, no VM action
  - Intent-based creation — "I need a VM for data science" → VM created
  - Ambiguous stop — "stop the running one" with one running VM → correct VM stopped
  - Rate limiting — 11 rapid commands → 429 on 11th
  - Dark theme — all pages show dark background
  - Status badges — VM list response shows colored Running/Stopped/Error labels

- [ ] T024 Run full backend test suite: `cd backend && pytest -q` — expected **22+ passed**, 0 failed; fix any regressions before closing

**Checkpoint**: All pages dark themed. Login shows role-selection cards. Full test suite green. Quickstart smoke tests documented.

---

## Dependency Graph

```
Phase 1: Setup
  T001
  └─► Phase 2: Foundational
       T002 (schemas)
       └─► T003 (ai_service) ──► T004 (route) ──► T005 (main.py)
       T006 [P] (frontend types)
       └─► Phase 3: US1 Tests ──► Phase 4: US2 Tests ──► Phase 5: US3 Tests
            T007                  T008                   T009
            └─► Phase 6: US4 (chat + prompt redesign)
                 T010 (SYSTEM_PROMPT) ──► T011 (tests)
            └─► Phase 7: US5 (rate limit + pipeline tests)
                 T012
       └─► Phase 8: Frontend
            T013 (page) ──► T014 (chat) ──► T015 (greeting) ──► T019 (chat behavior) ──► T020 (styling)
            T016 [P] (nav)  │  T017 [P] (login redirect)  │  T018 [P] (dashboard redirect)
       └─► Phase 9: Polish
            T021 [P] (global theme)  │  T022 [P] (auth redesign)  │  T023 [P] (quickstart)
            T024 (full suite — after all above)
```

### Critical Path

```
T001 → T002 → T003 → T004 → T005 → T007 → T008 → T009 → T010 → T012
                                                                       └─► T024
```

### Parallel Opportunities

```
After T003 completes:
  - T004 + T007 can start together (route + tests both depend on service)
  - T006 (frontend types) anytime after Phase 1

After T014 completes:
  - T015, T016, T017, T018 can all run in parallel (different files)

Phase 9:
  - T021, T022, T023 all parallel (different files)
  - T024 must be last
```

---

## Notes

- **T003 is the most critical task** — it orchestrates 5 subsystems (rate limiter, Groq client, JSON parser, Pydantic validator, VM service dispatcher) plus dual logging. ~300 lines.
- **T010 is the most impactful behavioral task** — it controls all AI behaviors: chat fallback, intent inference, ambiguity resolution, config-to-create. Run existing tests after T010 to confirm no regressions.
- **T019 and T020 both modify `ai-chat.tsx`** — run T019 first (functional), then T020 (styling).
- **No new database migrations** — do not modify `supabase/migrations/`. All tables from spec 001.
- **`model_dump(mode="json")`** required on all AI validator schemas — UUIDs must serialize as strings.
- **Log before return** — both `_log_ai_usage` and `_log_action` must be called before the final return or re-raise.
- **T022 does not change auth logic** — only the visual layout. `signInWithPassword` call is identical.
- **max_tokens=512** (not 256) — bumped to support longer chat responses and intent-inferred creation confirmations.
