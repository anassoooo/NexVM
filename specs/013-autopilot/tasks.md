# Tasks — Spec 013 NexVM Autopilot

**Branch**: `013-autopilot`
**Total tasks**: 14

| ID | Title | Feature | Est. | Status |
|---|---|---|---|---|
| T001 | Constitution v1.2.0 (§XIV), migration 005 `agent_runs`, unique VM names per user | all | 1 h | pending |
| T002 | Tool registry + VMBackend protocol + LiveBackend | F1 | 3 h | pending |
| T003 | World simulator | F2 | 3 h | pending |
| T004 | Planner loop with interception, budgets, conversation context | F1 | 4 h | pending |
| T005 | Diagnostics | F5 | 2 h | pending |
| T006 | Trace recorder + run store | F6 | 2 h | pending |
| T007 | Executor + repair | F3, F4 | 3 h | pending |
| T008 | `/api/v1/agent` routes | F3, F6 | 2 h | pending |
| T009 | Unit tests: ScriptedLLM + FakeBackend (planner, simulator, executor, routes) | all | 4 h | pending |
| T010 | Eval suite: scenarios, runner, report, baseline | F7, F8 | 4 h | pending |
| T011 | Frontend: plan-and-approve chat | F3 | 4 h | pending |
| T012 | Frontend: runs list + trace timeline | F6 | 3 h | pending |
| T013 | CI: agent eval job; docs | F7 | 1.5 h | pending |
| T014 | Verify: checks + live run of eval suite + manual UI test | all | 2 h | pending |

Each task is done when its tests pass and `ruff check .` is clean.
