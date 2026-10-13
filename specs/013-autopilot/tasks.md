# Tasks — Spec 013 NexVM Autopilot

**Branch**: `013-autopilot`
**Total tasks**: 14

| ID | Title | Feature | Est. | Status |
|---|---|---|---|---|
| T001 | Constitution v1.2.0 (§XIV), migration 005 `agent_runs`, unique VM names per user | all | 1 h | done |
| T002 | Tool registry + VMBackend protocol + LiveBackend | F1 | 3 h | done |
| T003 | World simulator | F2 | 3 h | done |
| T004 | Planner loop with interception, budgets, conversation context | F1 | 4 h | done |
| T005 | Diagnostics | F5 | 2 h | done |
| T006 | Trace recorder + run store | F6 | 2 h | done |
| T007 | Executor + repair | F3, F4 | 3 h | done |
| T008 | `/api/v1/agent` routes | F3, F6 | 2 h | done |
| T009 | Unit tests: ScriptedLLM + FakeBackend (planner, simulator, executor, routes) | all | 4 h | done |
| T010 | Eval suite: scenarios, runner, report, baseline | F7, F8 | 4 h | in progress — 37/65 recorded (Groq daily quota) |
| T011 | Frontend: plan-and-approve chat | F3 | 4 h | done |
| T012 | Frontend: runs list + trace timeline | F6 | 3 h | done |
| T013 | CI: agent eval job; docs | F7 | 1.5 h | done |
| T014 | Verify: checks + live run of eval suite + manual UI test | all | 2 h | pending |

Each task is done when its tests pass and `ruff check .` is clean.

## Notes (2026-10-13)

- First live eval: 33/37 passed before the Groq free-tier daily limit (200k tokens) stopped the run.
  Of the 4 failures: 2 were rate-limit errors, 1 was a malformed tool call (now retried, T004),
  1 was an ambiguous scenario, reworded and documented in `evals/scenarios.py`.
- Cost finding: gpt-oss-20b queues one step per turn (k8s lab: 7 calls, ~15k tokens). Try Groq's
  `parallel_tool_calls` once quota allows, and measure the effect with the eval suite.
