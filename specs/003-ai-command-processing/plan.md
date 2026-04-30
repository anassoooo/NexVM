# Implementation Plan: AI Command Processing

**Branch**: `003-ai-command-processing` | **Date**: 2026-04-07 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `/specs/003-ai-command-processing/spec.md`  
**Depends on**: `002-vm-management` fully complete — VM service layer (create_vm, start_vm, stop_vm, delete_vm, list_vms) all in place.

---

## Modification Plan: Free Conversation Mode

**Date**: 2026-04-15 | **Status**: Planned

### What changes

Users can now talk freely with the AI assistant. The AI determines intent and either executes a VM action (existing behavior) or responds conversationally — answering general questions, explaining concepts, providing guidance — without triggering any VM operation.

### Approach

Add a `chat` action to the existing JSON contract. The LLM returns `{"action": "chat", "message": "..."}` for non-VM requests. This preserves the JSON pipeline (§IV), the validation gate (§I/§3.2), and full observability (§III). No new endpoints, tables, or services.

### Constitution re-check

| Principle / Rule | Impact | Status |
|---|---|---|
| §I + §3.1 — No direct execution from AI | `chat` has no execution path | **PASS** |
| §III — Full Observability | `chat` logged to `ai_usage` and `logs` | **PASS** |
| §IV — Structured AI Output Contract | `chat` is a new validated JSON action type | **PASS** |
| §3.3 — Whitelisted Actions | Whitelist extended to include `chat` | **PASS** |
| §V — YAGNI | One schema class, one dispatch branch, zero new infrastructure | **PASS** |

### Files to change

```text
backend/app/
├── models/schemas.py           ADD  AIChat(action: Literal["chat"], message: str 1-2000)
└── services/ai_service.py
    ├── ALLOWED_ACTIONS          ADD  "chat"
    ├── ACTION_SCHEMAS           ADD  "chat": AIChat
    ├── SYSTEM_PROMPT            REWORK — use `chat` as default fallback; `error` only for unresolvable
    ├── _execute_action()        ADD  "chat" branch → return validated["message"]
    └── max_tokens               BUMP 256 → 512

frontend/components/ai-chat.tsx
    ├── action badge             HIDE badge for "chat" action (no action label needed for conversational replies)
    └── character counter        UPDATE limit display from 500 → 2000
```

### Spec artifacts updated

- `spec.md` — User Story 5 added; FR-004 updated (6 actions); FR-019 added; edge cases added
- `research.md` — §7 added (free conversation mode design decisions)
- `data-model.md` — `AIChat` schema added; data flow updated
- `contracts/ai-api.md` — `chat` action shape added; `error` behaviour clarified

---

## Summary

Build the AI command interface for myVMS. This plan covers: Pydantic schemas for AI request/response and per-action validation, an AI service layer integrating Groq with rate limiting, system prompt engineering, JSON validation, and VM service dispatch, a FastAPI route exposing one endpoint, backend tests with mocked Groq API, and a frontend AI chat page.

No new database tables or migrations are needed — the `ai_usage` and `logs` tables from spec 001 are the complete persistence layer for this feature.

---

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript 5.x (frontend)  
**New Backend Files**: `services/ai_service.py`, `routes/ai.py` (+ update `main.py`, `models/schemas.py`)  
**New Frontend Files**: `components/ai-chat.tsx`, `app/ai/page.tsx` (+ update `layout.tsx`, `types/index.ts`)  
**Existing Reused Files**: `dependencies.py` (`get_current_user`), `models/enums.py` (`LogAction.ai_command`), `services/vm_service.py` (all CRUD functions), `db.py` (`get_supabase_client`)  
**Storage**: Supabase PostgreSQL — `ai_usage` table (AI logs), `logs` table (audit trail)  
**Testing**: pytest + unittest.mock.patch for Groq SDK  
**Groq Model**: `llama-3.3-70b-versatile`, temperature=0, max_tokens=256  
**Rate Limiting**: In-memory sliding window, 10 requests/60 seconds per user  
**Constraints**: No streaming; no conversation history to Groq; synchronous execution

---

## Constitution Check

| Principle / Rule | Requirement | Status | Notes |
|---|---|---|---|
| §II — Auth Before Everything | AI endpoint protected by JWT | **PASS** | Uses `Depends(get_current_user)` |
| §VI.3 — No direct frontend DB writes | Frontend calls backend API | **PASS** | All AI actions go through `POST /api/v1/ai/command` |
| §XI.1 — Auth Required | Endpoint requires valid JWT | **PASS** | No unauthenticated AI access |
| §XI.2 — Input Validation | Pydantic validates at API boundary | **PASS** | Request body validated; AI output validated by Pydantic before execution |
| §XII.1 — Mandatory Logging | Log before returning response | **PASS** | Dual logging to `ai_usage` and `logs` tables |
| §V — YAGNI | No streaming, no history, no multi-step | **PASS** | Single prompt/response, no conversation context sent to LLM |

**All gates pass. No violations. Proceeding to implementation.**

---

## Project Structure

### Documentation (this feature)

```text
specs/003-ai-command-processing/
├── plan.md              ✅ This file
├── spec.md              ✅ Feature specification
├── research.md          ✅ Phase 0 output
├── data-model.md        ✅ Schema and data flow
├── quickstart.md        ✅ Smoke test guide
├── tasks.md             ✅ Task breakdown
├── contracts/
│   └── ai-api.md        ✅ API contract
└── checklists/
    ├── requirements.md  ✅ Spec quality gate
    └── implementation.md ✅ Pre/post implementation gate
```

### Source Code Changes

```text
backend/
├── app/
│   ├── main.py                  MODIFY — include AI router
│   ├── models/
│   │   └── schemas.py           MODIFY — add AICommandRequest, AICommandResponse, 4 AI validator schemas
│   ├── routes/
│   │   └── ai.py                CREATE — POST /command endpoint
│   └── services/
│       └── ai_service.py        CREATE — Groq integration, validator, rate limiter, executor, dual logging
└── tests/
    └── test_ai_service.py       CREATE — 13 mocked Groq test cases

frontend/
├── app/
│   └── ai/
│       └── page.tsx             CREATE — AI page (server component, auth check)
├── components/
│   └── ai-chat.tsx              CREATE — chat UI client component
├── app/
│   └── layout.tsx               MODIFY — add "AI" nav link
└── types/
    └── index.ts                 MODIFY — add AICommandResponse interface
```

**No database migrations required.**

---

## Complexity Tracking

No constitution violations. All tasks within 4-hour complexity budget (§10.3). Synchronous Groq calls avoid async complexity for MVP. In-memory rate limiter avoids Redis dependency.
