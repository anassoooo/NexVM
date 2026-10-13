# Implementation Plan: NexVM Autopilot

**Branch**: `013-autopilot` | **Date**: 2026-10-13 | **Spec**: `specs/013-autopilot/spec.md`

## Summary

A new `app/agent/` package: typed tool registry, a planner that intercepts write calls,
a world simulator, deterministic executor with one-shot repair, diagnostics, tracing and
run storage. New `/api/v1/agent` routes and an `agent_runs` table. The `/ai` page becomes a
plan-and-approve chat with a run timeline viewer. An eval suite (`backend/evals/`) measures
the agent against an in-memory VM backend and runs in CI.

## Technical Context

**Language/Version**: Python 3.12+, TypeScript 5.x
**LLM**: Groq chat completions with native tool calling; model from `GROQ_MODEL`
(`openai/gpt-oss-20b`; probe: 0.8 s, valid tool calls)
**Storage**: Supabase — new `agent_runs` table (migration 005)
**Testing**: pytest with a scripted LLM (no network) + live eval runner
**Constraints**: no new runtime dependencies; ruff, tsc, lint, build pass; existing 172 tests pass

## Constitution Check

| Principle | Status | Notes |
|---|---|---|
| §II Auth Before Everything | ✅ PASS | All `/agent` routes use `get_current_user` |
| §IV AI-First UX | ✅ PASS | Strengthens the chat as the primary surface |
| §V YAGNI | ✅ PASS | Every component maps to an FR in spec 013; no streaming, no guest shell |
| §VI.1 Separation of Concerns | ✅ PASS | Planning/execution in backend; UI renders plans and traces |
| §VI.2 API Versioning | ✅ PASS | New routes under `/api/v1/agent`; `/ai/command` unchanged |
| §VI.3 No Direct Frontend DB Writes | ✅ PASS | UI calls FastAPI only |
| §VII Data Access Rules | ✅ PASS | `agent_runs`: RLS, `authenticated` SELECT-only, writes by backend |
| §IX Backend Conventions | ✅ PASS | Sync handlers; executor runs in a background thread |
| §XI.3 Command Whitelist | ✅ PASS | Executor calls existing `vm_service` functions only |
| §XI.5 VirtualBox Resource Isolation | ✅ PASS | Names resolved to the user's own rows, then `vbox_id` |
| §XI.6 Destructive AI Actions Require Confirmation | ✅ PASS | Every write requires plan approval |
| §XII Observability & Logging | ✅ PASS | VM actions logged by `vm_service`; usage to `ai_usage`; trace per run |
| §XIV AI Engineering | ✅ PASS | Evals, tracing, server-side identity, no direct LLM writes |
| §X.3 Task Ceiling | ✅ PASS | Largest task ~4 h (T004 planner) |

**Gate result**: ALL PASS — proceed to tasks.

## Design

### D1 — Ports and adapters

```text
app/agent/
├── tools.py        ToolSpec registry: name, description, args model, kind (read/write), risk
├── backend.py      VMBackend protocol + LiveBackend (wraps vm_service, logs, quota)
├── world.py        World snapshot + Simulator (preconditions, quota, ports, name uniqueness)
├── diagnostics.py  Deterministic findings from a VM + metrics + recent logs
├── llm.py          LLM protocol + GroqLLM (tool calling, usage, timing)
├── planner.py      Agent loop with write interception and simulator feedback
├── executor.py     Approved plan → backend calls; step statuses; repair hand-off
├── trace.py        Span recorder
├── store.py        agent_runs persistence (Supabase)
└── prompts.py      System prompt
```

The planner and executor depend only on the `LLM` and `VMBackend` protocols. Production wires
`GroqLLM` + `LiveBackend`; tests wire `ScriptedLLM` + `FakeBackend`; evals wire `GroqLLM` +
`FakeBackend`. Same agent code in all three.

### D2 — Plan by interception

Write tools are real, typed functions in the schema the model sees, so arguments are
constrained by JSON schema rather than prompt text. When the model calls one, the planner:
1. validates arguments with the Pydantic model → error message back to the model on failure
2. applies the step to the simulator → error back on precondition failure
3. appends the step and answers the tool call with `queued as step N — not executed yet`
   plus the simulated effect.

This lets the model build multi-step plans that depend on earlier steps, and fix its own
mistakes inside the same planning turn.

### D3 — Execution and repair

`POST /agent/runs/{id}/approve {plan_version}` → status `running` → executor thread.
Each step re-resolves the VM by name for the current user and calls `vm_service`. The run
row is updated after every step. On failure: if no repair used, call the planner in repair
mode (completed steps + error + fresh world) → plan version + 1 → `needs_approval`.

### D4 — Run lifecycle

```
answered                       (no write steps)
needs_approval ─approve─► running ─► completed
      │                      │
      └─cancel─► cancelled   └─step fails─► needs_approval (repair) | failed
```

### D5 — Data model (migration 005)

`agent_runs(id, user_id → auth.users, conversation_id, prompt, status, answer, plan jsonb,
plan_version int, findings jsonb, trace jsonb, model, total_tokens, latency_ms, repairs int,
error, created_at, updated_at)`; index on `(user_id, created_at desc)` and `conversation_id`;
RLS: user reads own rows; grants: `authenticated` SELECT only.

### D6 — Evaluation

`backend/evals/`: `scenarios.py` (fixtures + expectations), `fake_backend.py`, `run.py`
(CLI: `python -m evals.run --model X`), `baseline.json`. Scoring is deterministic over the
produced plan and answer. CI job `agent-evals` runs when the `GROQ_API_KEY` secret is set.

## Risks

| Risk | Mitigation |
|---|---|
| Model invents arguments | Typed schemas + validation errors fed back (seen in the probe with an untyped tool) |
| Prompt injection via VM names/logs | Results wrapped as data; approval always required; red-team evals |
| Plan valid in simulation, fails for real (VirtualBox) | Executor re-validates; one repair round |
| Long planning latency | Turn/tool budgets; small fast model by default |
| Duplicate VM names break name-based steps | Simulator rejects duplicates; `create_vm` rejects a duplicate name for the same user |
