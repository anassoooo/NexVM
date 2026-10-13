# Spec 013 — NexVM Autopilot

**Branch**: `013-autopilot`
**Date**: 2026-10-13
**Priority**: P1 — flagship AI capability
**Constitution**: v1.2.0 (§XIV AI Engineering added for this spec)

## Overview

Today the assistant turns one message into one JSON action (`ai_service.py`). It cannot
look before it acts, cannot do multi-step work, forgets the conversation, and nobody can
measure how often it is right.

Autopilot replaces it with an agent that **plans with real tools, proves its plan in a
simulator, asks for approval, executes deterministically, repairs failures, explains VM
problems from live data, and is measured by an evaluation suite that runs in CI**.

```
User ─► Planner (LLM + tools) ──► Plan ──► Approval ──► Executor (no LLM) ──► VMs
            │   ▲                   ▲                        │
   read tools│   │ errors           │ repaired plan          │ step failed
            ▼   │                   └──── Repair (LLM) ◄─────┘
         World state ─► Simulator
```

---

## F1 — Tool-using Planner

### Problem

One action per message; the model must guess VM state from a JSON dump; free-form JSON output
breaks easily.

### Feature

The model uses native tool calling. **Read tools** run immediately (list VMs, diagnose, list
snapshots, ISOs, recent activity, quota). **Write tools** are intercepted: they become plan
steps instead of running.

### Functional Requirements

| ID | Requirement |
|---|---|
| FR-101 | Tools are typed (Pydantic argument models); the JSON schema sent to the model is generated from them |
| FR-102 | Read tools execute during planning; their results go back to the model |
| FR-103 | Write tool calls are never executed during planning; each valid call becomes a plan step |
| FR-104 | Invalid arguments or failed simulation are returned to the model as a tool error so it can correct itself |
| FR-105 | VMs are referenced by name; a step may reference a VM created by an earlier step |
| FR-106 | The user's identity comes from the server context; no tool accepts a user id |
| FR-107 | Planning is bounded: max 8 model turns, max 12 plan steps, max 24 tool calls |
| FR-108 | The last 6 turns of the same conversation are given to the model as context |
| FR-109 | Replies in the user's language |

## F2 — Plan Simulator

| ID | Requirement |
|---|---|
| FR-201 | Each proposed step is applied to a copy of the user's world (VMs, quota, ports) |
| FR-202 | Checks: VM exists / name unique, state preconditions, VM count and disk quota, host-port conflicts (real and within the plan), argument ranges |
| FR-203 | Simulated state flows to later steps (create → stopped → start → running) |
| FR-204 | Each accepted step records its simulated effect, shown to the user |

## F3 — Approval and Deterministic Execution

| ID | Requirement |
|---|---|
| FR-301 | A plan with any write step is shown for approval; nothing changes until approved |
| FR-302 | Steps show a risk level: `low`, `costly` (creates resources), `destructive` (deletes data or powers off) |
| FR-303 | The plan shows a resource summary (new VMs, RAM, CPU, disk vs quota) |
| FR-304 | Approval names the plan version; approving an outdated version returns 409 |
| FR-305 | The executor runs steps in order without the LLM, re-resolving names and calling the existing VM services (ownership, logging and validation apply) |
| FR-306 | Step status (`pending`, `running`, `done`, `failed`, `skipped`) is persisted and polled by the UI |
| FR-307 | A run can be cancelled before approval or between steps |

## F4 — Self-repair

| ID | Requirement |
|---|---|
| FR-401 | When a step fails, the planner gets the error, the completed steps and the fresh world, and proposes a revised plan for the rest |
| FR-402 | The revised plan needs a new approval |
| FR-403 | At most one repair per run; after that the run fails with the error shown |

## F5 — Diagnostics

| ID | Requirement |
|---|---|
| FR-501 | `diagnose_vm` returns deterministic findings with severity (`info`, `warning`, `critical`) |
| FR-502 | Checks: error state and message, RAM and CPU pressure on running VMs, ISO still attached with DVD-first boot, recent failed actions, disk quota pressure |
| FR-503 | The model explains findings and may propose a fix as a normal plan |

## F6 — Observability

| ID | Requirement |
|---|---|
| FR-601 | Every run stores a trace: each model call and tool call with duration, tokens and outcome |
| FR-602 | Runs list and run detail endpoints; the UI shows a timeline (waterfall) per run |
| FR-603 | Totals per run: latency, tokens, model |

## F7 — Evaluation Suite

| ID | Requirement |
|---|---|
| FR-701 | ≥ 60 scenarios: single actions, multi-step, reference resolution, clarification, diagnostics, repair, multilingual, safety red-team |
| FR-702 | Scenarios run against an in-memory VM backend; no VirtualBox or database needed |
| FR-703 | Scoring per scenario: expected plan steps (tool + key args), forbidden tools, clarification expected, answer contains |
| FR-704 | Report: pass rate per category, safety pass rate, avg latency, tokens; JSON + Markdown |
| FR-705 | CI runs deterministic agent tests on every push; the live eval runs when a `GROQ_API_KEY` secret exists, and fails if the pass rate drops more than 5 points below the committed baseline |

## F8 — Safety

| ID | Requirement |
|---|---|
| FR-801 | Tool results are wrapped as data; instructions found in VM names, logs or user text cannot trigger execution (approval is always required) |
| FR-802 | Red-team scenarios: prompt injection, other users' VM ids, "delete everything", oversized requests, off-topic requests |
| FR-803 | The planner can only see and plan for the current user's VMs |

## Out of Scope

- Streaming tokens to the UI (runs are polled)
- Executing shell commands inside guest VMs
- Removing the old `/api/v1/ai/command` endpoint (kept for compatibility, no longer used by the UI)
