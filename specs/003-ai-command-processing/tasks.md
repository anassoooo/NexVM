# Tasks: AI Command Processing

**Input**: Design documents from `/specs/003-ai-command-processing/`  
**Prerequisites**: `002-vm-management` complete ✅ — VM service layer (create_vm, start_vm, stop_vm, delete_vm, list_vms), auth middleware, Groq SDK in requirements.txt, ai_usage table, LogAction.ai_command enum all in place.

**Tests**: Backend unit tests for ai_service.py with mocked Groq SDK.

**Organization**: Backend foundation must be complete before frontend integration.

## Format: `[ID] [P?] Description`

- **[P]**: Can run in parallel (different files, no shared dependencies)

---

## Phase 1: Backend Foundation

**Purpose**: Implement Pydantic schemas, AI service, and HTTP route.

- [x] T001 Add AI schemas to `backend/app/models/schemas.py`:
  - `AICommandRequest(prompt: str)` — Field(min_length=1, max_length=500)
  - `AICommandResponse(action: str, result: str, ai_response: dict[str, Any])`
  - `AICreateVM(action: Literal["create_vm"], name, os, ram)` — same regex/range as VMCreate
  - `AIStartVM(action: Literal["start_vm"], vm_id: uuid.UUID)`
  - `AIStopVM(action: Literal["stop_vm"], vm_id: uuid.UUID)`
  - `AIDeleteVM(action: Literal["delete_vm"], vm_id: uuid.UUID)`

- [x] T002 Create `backend/app/services/ai_service.py` with:
  - `SYSTEM_PROMPT` template — forces JSON-only output, includes all 4 action schemas + error action, has `{vm_list_json}` placeholder
  - `_rate_limit_store: dict[str, list[float]]` — module-level in-memory store
  - `_check_rate_limit(user_id)` — sliding window, 10/min, raises 429
  - `_build_system_prompt(user_id)` — calls `vm_service.list_vms()`, injects VM list JSON
  - `_call_groq(system_prompt, user_prompt) -> (raw_text, tokens)` — catches `groq.APIError` → 503
  - `_validate_ai_response(raw_json) -> dict` — json.loads, action whitelist, Pydantic validate, model_dump(mode="json")
  - `_execute_action(validated, user_id) -> str` — dispatches to vm_service functions
  - `_log_ai_usage(user_id, prompt, response, tokens)` — insert to ai_usage table
  - `_log_action(user_id, target, status, message)` — insert to logs table with action=ai_command
  - `process_ai_command(prompt, user_id) -> AICommandResponse` — orchestrates all above

- [x] T003 Create `backend/app/routes/ai.py`:
  - Single endpoint: `POST /command` → `ai_service.process_ai_command()`
  - Uses `Depends(get_current_user)`

- [x] T004 Update `backend/app/main.py`:
  - `app.include_router(ai_router, prefix="/api/v1/ai", tags=["ai"])`

**Checkpoint**: `python -c "from app.main import app"` succeeds. `POST /api/v1/ai/command` appears in route list.

---

## Phase 2: Backend Tests

**Purpose**: Verify all AI service paths using mocked Groq API.

- [x] T005 Create `backend/tests/test_ai_service.py` with 13 test cases:

  **Happy paths**:
  - (1) create_vm — Groq returns valid JSON → VM created → logged to ai_usage + logs
  - (2) start_vm — Groq returns valid JSON → VM started
  - (3) stop_vm — Groq returns valid JSON → VM stopped
  - (4) delete_vm — Groq returns valid JSON → VM deleted

  **Failure paths**:
  - (5) Groq returns non-JSON text → 400
  - (6) Groq returns unknown action → 400
  - (7) Groq returns `{"action": "error", "message": "..."}` → 400 with AI message
  - (8) Groq returns create_vm with invalid RAM (99999) → 400
  - (9) Groq API error (APIError) → 503
  - (10) Rate limit: 11th call within 60s → 429
  - (11) VM service raises 409 → 409 propagates; ai_usage still logged
  - (12) Groq returns name with special chars → 400
  - (13) VM list injected in system prompt — assert Groq called with VM name in system message

**Checkpoint**: `pytest backend/tests/test_ai_service.py -v` — all 13 pass.

---

## Phase 3: Frontend

**Purpose**: AI chat page and interactive chat component.

- [x] T006 Create `frontend/components/ai-chat.tsx` — client component:
  - `messages` state: `{id, role, content, action?, error?}[]`
  - Input form: text field (maxLength=500), character counter, submit button
  - Calls `api.post<AICommandResponse>("/api/v1/ai/command", { prompt })`
  - User messages right-aligned (blue); assistant messages left-aligned (gray); errors in red
  - Action badge on assistant messages (e.g., "create_vm" pill)
  - "Thinking..." indicator while loading
  - Submit disabled when loading or input empty

- [x] T007 Create `frontend/app/ai/page.tsx` — server component:
  - Auth check via `supabase.auth.getUser()`, redirect to `/login` if unauthenticated
  - Renders `<AIChat />`

- [x] T008 Update `frontend/app/layout.tsx`:
  - Add "AI" nav link after "VMs" link

- [x] T009 [P] Add `AICommandResponse` type to `frontend/types/index.ts`

**Checkpoint**: `/ai` loads, redirects unauthenticated users, chat UI renders, commands execute.

---

## Dependencies & Execution Order

```text
Phase 1 (Backend Foundation)
    T001 (schemas) → T002 (ai_service) → T003 (route) → T004 (main.py)
    ↓
Phase 2 (Backend Tests) ← can overlap with Phase 3 once T002 is done
    ↓
Phase 3 (Frontend) ← requires Phase 1 backend for API calls
```

### Within Phase 1
```
T001 → T002 → T003 → T004
```
Each step imports from the previous.

### Within Phase 3
```
T006 [P] + T009 [P] → T007 → T008
```
T006 and T009 are independent. T007 imports T006.

---

## Notes

- **T002** is the most critical task — it orchestrates five subsystems (rate limiter, Groq client, JSON parser, Pydantic validator, VM service dispatcher) plus dual logging. ~150 lines.
- **T001 must precede T002** — service imports the schemas.
- **No new migrations** — do not modify `supabase/migrations/`. Schema from spec 001 is complete.
- **model_dump(mode="json")** is required on AI validator schemas — UUIDs must serialize as strings.
- **Log before return** — both `_log_ai_usage` and `_log_action` must be called before the final return or re-raise.
