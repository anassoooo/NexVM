<!--
SYNC IMPACT REPORT
==================
Version change: 1.0.0 → 1.1.0
Bump type: MINOR — multiple new sections added with materially expanded guidance; no principles
  removed or redefined in backward-incompatible ways.
Modified principles:
  - Principle I (Security-Gated AI Execution) → preserved; detailed rules now also in §3 AI Safety Rules
  - Principle II (Authentication Before Everything) → preserved; detailed rules now also in §11 Security Rules
  - Principle III (Full Observability) → preserved; detailed rules now also in §8 Analytics and §12 Logging
  - Principle IV (Structured AI Output Contract) → preserved; detailed rules now also in §3 AI Safety Rules
  - Principle V (Simplicity — YAGNI) → preserved; detailed rules now also in §10 Performance & Scope Control
Added sections:
  - §1  Purpose (rationale and scope of this constitution)
  - §3  AI Safety Rules (whitelisted actions, no dynamic injection, validation gate)
  - §4  Backend Rules (FastAPI layered architecture, no logic in routes, idempotency)
  - §5  VM Execution Rules (VBoxManage command mapping, state sync, execution logging)
  - §6  Database Rules (schema consistency, referential integrity, write-path enforcement)
  - §7  Frontend Rules (UI-only, API-driven, error visibility)
  - §8  Analytics Rules (mandatory tracking, minimal viable metrics)
  - §9  Code Generation Rules (agent role assignments: Claude / Gemini / GLM)
  - §10 Performance & Scope Control (7-day timeline, MVP-only, 4-hour complexity budget)
  - §11 Security Rules (auth required, input validation, command safety)
  - §12 Logging & Debugging (mandatory logging, traceable log chain)
  - §13 Violation Policy (reject-and-rewrite enforcement)
  - §14 Final Rule (ambiguity resolution)
Removed sections: None
Templates reviewed:
  - .specify/templates/plan-template.md  ✅ Constitution Check section present; gates align with
      all expanded principles
  - .specify/templates/spec-template.md  ✅ FR/SC structure compatible; Functional Requirements
      pattern aligns with new layer-specific rules
  - .specify/templates/tasks-template.md ✅ Phase 2 Foundational tasks already cover auth,
      logging, and error handling as required by new sections
Follow-up TODOs: None — all fields resolved from user input and prior repo context
-->

# myVMs Constitution

## §1 Purpose

This constitution defines the mandatory engineering principles, constraints, and rules governing
the development of the myVMs platform. It supersedes all informal agreements, verbal decisions,
and undocumented practices.

All agents — human and AI — MUST strictly follow these rules when generating code, architecture,
or specifications. Ignorance of this document is not an acceptable justification for a violation.

## §2 Core Principles

### I. Security-Gated AI Execution (NON-NEGOTIABLE)

The AI layer MUST never execute shell commands directly. All natural-language requests MUST be
converted to structured JSON by the AI Execution Agent, then validated by the Backend Executor
before any VBoxManage command is invoked.

**Rules:**
- AI output MUST be structured JSON; free-form shell strings are forbidden.
- The Backend Executor MUST validate every AI-produced command against an allowlist of safe
  VBoxManage operations before execution.
- Any unrecognized or malformed AI output MUST be rejected with an error returned to the user —
  never silently ignored or partially executed.

**Rationale:** Allowing unrestricted AI→shell paths creates remote-code-execution risk. A JSON
contract + server-side validation is the only safe boundary.

### II. Authentication Before Everything

Every API endpoint and VM operation MUST be protected by Supabase-based authentication.
Unauthenticated requests MUST be rejected at the API boundary before any business logic runs.

**Rules:**
- No VM lifecycle operation (create/start/stop/delete) is reachable without a valid authenticated
  session.
- Admin-only routes MUST additionally verify admin role claims in the JWT.
- The frontend MUST redirect unauthenticated users to the login page before rendering any VM
  management UI.

**Rationale:** VMs are compute resources with real costs and security impact. Unauthenticated
access would allow arbitrary resource creation and abuse.

### III. Full Observability

Every VM lifecycle event and every AI interaction MUST be persisted to the database. Silent
operations are forbidden.

**Rules:**
- VM operations (create/start/stop/delete) MUST write a record to the `logs` table with user ID,
  VM ID, action, timestamp, and outcome.
- AI requests and responses MUST be recorded in the `ai_usage` table with user ID, prompt
  summary, JSON output, and success/failure status.
- API errors MUST be logged with sufficient context to reproduce the failure.

**Rationale:** Observability enables admin analytics, abuse detection, and post-incident
debugging — all core product requirements.

### IV. Structured AI Output Contract

The interface between the AI layer and the backend MUST be a typed JSON schema. Prompt design
MUST target JSON-only responses; any non-JSON AI response MUST be treated as a failure.

**Rules:**
- The AI Execution Agent MUST be prompted with an explicit output schema (action type, parameters,
  target VM ID).
- The Backend Executor MUST deserialize and validate the JSON against the schema before mapping
  to a VBoxManage call.
- Schema changes MUST be versioned and backward-compatible unless a major version bump is
  declared.

**Rationale:** A stable contract decouples AI prompt engineering from backend execution logic and
makes the system auditable and testable independently.

### V. Simplicity — YAGNI

Features MUST NOT be built speculatively. Every new capability MUST map to an explicit user story
in the product spec. Premature abstraction and gold-plating are violations.

**Rules:**
- No new service, module, or abstraction layer may be introduced without a concrete, accepted
  user story that requires it.
- The system MUST start with the minimum schema (users, vms, logs, ai_usage) and expand only
  when a new story demands it.
- Dependencies MUST be justified; transitive dependencies that do not serve an active requirement
  MUST be removed.

**Rationale:** Complexity compounds. The platform targets students who need a working MVP fast;
over-engineering delays delivery and increases maintenance burden.

## §3 AI Safety Rules

These rules expand on Core Principle I and IV. They are CRITICAL and non-waivable.

**3.1 No Direct Execution from AI**
- AI MUST NEVER execute shell commands directly.
- All AI outputs MUST be structured JSON; no free-form text reaching any execution layer.

**3.2 Mandatory Validation Layer**
- Every AI output MUST be validated before execution.
- Invalid or unknown actions MUST be rejected and MUST NOT be partially executed.

**3.3 Whitelisted Actions Only**

The only permitted AI-initiated VM actions are:
- `create_vm`
- `start_vm`
- `stop_vm`
- `delete_vm`

No other actions are permitted. Any action not in this list MUST be rejected at the validation
layer.

**3.4 No Dynamic Code Injection**
- AI MUST NOT generate executable scripts.
- `eval()`, `exec()`, and dynamic shell execution are strictly forbidden in any AI-touched code
  path.

## §4 Backend Rules (FastAPI)

**4.1 Layered Architecture Required**

All backend code MUST follow this strictly ordered hierarchy:

```
API Layer → Service Layer → Execution Layer → Data Layer
```

Skipping layers or bypassing this order is a violation.

**4.2 No Business Logic in Routes**
- Routes MUST only handle HTTP request parsing and response serialization.
- All domain logic MUST reside inside service modules.

**4.3 Controlled System Access**
- All system commands MUST go through a controlled wrapper module.
- Direct `subprocess` calls inside route handlers are forbidden.

**4.4 Idempotent Operations**
- Repeated identical requests MUST NOT corrupt system state.
- VM operations MUST check current state before executing to avoid double-execution.

## §5 VM Execution Rules (VirtualBox)

**5.1 Command Mapping Only**
- Each VM action MUST map to a predefined, hardcoded VBoxManage command string.
- Dynamic command construction from user input is forbidden.

**5.2 No Arbitrary Command Execution**
- Only the four predefined VBoxManage commands (mapped to create/start/stop/delete) are allowed.
- No other VBoxManage subcommands may be invoked at runtime.

**5.3 State Synchronization**
- VM state MUST always be reflected in the `vms` database table immediately after each operation.
- Stale state is a bug and MUST be treated as a violation of Principle III (Observability).

**5.4 Execution Logging**

Every VM action MUST be logged to the `logs` table with all of:
- `action` (one of the four whitelisted actions)
- `timestamp` (ISO 8601 UTC)
- `result` (`success` or `failure` with error message on failure)

## §6 Database Rules (Supabase)

**6.1 Schema Consistency**
- Tables MUST follow the defined schema: `users`, `vms`, `logs`, `ai_usage`.
- Dynamic schema changes at runtime are forbidden.

**6.2 Referential Integrity**
- All relations MUST be explicit via foreign keys (`user_id`, `vm_id`).
- Orphaned records are a schema violation.

**6.3 Write Operations**
- All writes MUST go through backend APIs.
- The frontend MUST NEVER write directly to the database.
- Direct Supabase client mutations from the frontend are forbidden for non-auth operations.

## §7 Frontend Rules (Next.js)

**7.1 No Business Logic**
- The frontend MUST handle UI rendering and user interaction only.
- VM logic, AI processing, and data validation are backend responsibilities.

**7.2 API-Driven Design**
- All data MUST be fetched from backend API endpoints.
- Direct Supabase database queries from frontend components are forbidden (auth excepted).

**7.3 State Management Simplicity**
- Complex global state MUST NOT be introduced unless a specific user story explicitly requires it.
- Prefer local component state combined with API fetching over global state managers.

**7.4 Error Visibility**
- All backend errors MUST be surfaced clearly to the user in the UI.
- Silent swallowing of API errors in UI components is a violation of Principle II.5 (Fail Fast).

## §8 Analytics Rules

**8.1 Mandatory Tracking**

The system MUST track all of:
- VM lifecycle events (create/start/stop/delete with outcome)
- AI requests (prompt summary, JSON output, success/failure)
- User activity (login events, VM actions per user)

**8.2 Minimal Viable Metrics**

For MVP, the system MUST expose at minimum:
- Total registered users
- Total VMs (active and historical)
- Total AI requests processed

**8.3 No Over-Engineering**
- Complex dashboards, real-time streaming analytics, and BI integrations are out of scope for MVP.
- Metrics MUST be derivable from the `logs` and `ai_usage` tables via simple queries.

## §9 Code Generation Rules (Agent Assignments)

These rules define which AI agent is responsible for which layer. Crossing these boundaries
requires explicit justification.

**9.1 Claude — Backend**
- Owns all FastAPI service code, route handlers, executor modules, and data layer.
- MUST follow FastAPI best practices and the service-based architecture defined in §4.
- MUST include input validation and structured logging in all generated code.

**9.2 Gemini — Frontend**
- Owns all Next.js component code, page layouts, and API integration hooks.
- MUST follow component-based design with strict separation of UI and API-fetching logic.

**9.3 GLM — Support**
- Restricted to utility functions and helper logic only.
- MUST NOT own any layer-critical code (routes, services, components).

## §10 Performance & Scope Control

**10.1 Time Constraint Awareness**
- All feature implementations MUST be completable within the 7-day MVP timeline.
- Any feature that cannot be completed within this window MUST be deferred or descoped.

**10.2 Feature Limitation**
- Only MVP features (those with an accepted user story) are permitted.
- Additional features requested mid-sprint MUST be rejected or added to a post-MVP backlog.

**10.3 Complexity Budget**
- If implementing a task is estimated to exceed 4 hours, it MUST be simplified before starting.
- Complexity escalation MUST be documented in the Complexity Tracking table of the plan.

## §11 Security Rules

These rules expand on Core Principle II. They are non-waivable.

**11.1 Authentication Required**
- Every API endpoint MUST require a valid Supabase JWT.
- No endpoint may be publicly accessible without explicit justification and constitution amendment.

**11.2 Input Validation**
- All inputs from external sources (HTTP requests, AI outputs, environment variables) MUST be
  validated before use.
- Validation MUST occur at the API boundary — not only inside services.

**11.3 Command Safety**
- User-supplied input MUST NEVER reach a system command string directly.
- All VBoxManage invocations MUST use the hardcoded command map defined in §5.1.

## §12 Logging & Debugging

**12.1 Mandatory Logging**
- Every critical action (VM operation, AI request, auth event, API error) MUST be logged.
- Logging MUST occur before returning any response so that failures during response serialization
  do not suppress the log entry.

**12.2 Debuggability**

Logs MUST enable full trace reconstruction of any incident:

```
User → Action → System Response
```

Each log entry MUST include: user ID, action type, timestamp, input summary, and outcome.

## §13 Violation Policy

Any code, specification, or architecture that violates this constitution MUST be:

1. **Rejected immediately** — no partial merging or "fix later" exceptions.
2. **Rewritten to comply** — the author (human or AI) is responsible for producing a
   compliant version before the work can proceed.

Security violations (§3 AI Safety, §11 Security) are **non-waivable**. No exception process
exists for these sections.

## §14 Final Rule

If there is any ambiguity in this constitution or in a specification:

> Choose the simplest, safest, and most deterministic solution.

When in doubt: less code, more validation, more logging.

## Technology Stack Constraints

The following technology choices are locked for MVP and MUST NOT be swapped without a constitution
amendment:

| Layer      | Technology              | Constraint |
|------------|-------------------------|------------|
| Frontend   | Next.js 14              | MUST use App Router; no Pages Router |
| Auth       | Supabase                | MUST use Supabase JWT; no custom auth |
| Backend    | FastAPI (Python)        | MUST expose REST; no GraphQL for MVP |
| VM Control | VirtualBox / VBoxManage | MUST use CLI interface; no libvirt |
| AI         | Groq API                | MUST receive/return JSON; no streaming UI for MVP |
| Database   | Supabase (Postgres)     | MUST use the four canonical tables: users, vms, logs, ai_usage |

Deviating from this stack MUST be raised as an amendment with a documented migration plan before
any code is written.

## Development Workflow

All work MUST follow this gated flow to ensure constitution compliance:

1. **Spec first** — a feature spec with user stories MUST exist before any implementation begins.
2. **Plan gate** — the implementation plan MUST include a Constitution Check section verifying
   the five core principles and all relevant layer rules are satisfied.
3. **Security review** — any change touching the AI execution path or authentication layer MUST
   be explicitly reviewed against §3 and §11 before merge.
4. **Observability check** — any new operation that can change VM state MUST include a
   corresponding log write (Principle III, §5.4, §12).
5. **No direct VBoxManage from AI** — all PRs to the AI/executor boundary MUST include evidence
   that §3.2 validation occurs before execution.
6. **Scope gate** — any new feature MUST be validated against §10 (Performance & Scope Control)
   before work begins.

## Governance

This constitution supersedes all other development practices and informal agreements. Amendments
require:

1. A written proposal describing the change, motivation, and impact on existing principles.
2. Review and approval before merging to main.
3. Version increment per semantic rules:
   - **MAJOR**: Backward-incompatible governance/principle removals or redefinitions.
   - **MINOR**: New principle or section added, or materially expanded guidance.
   - **PATCH**: Clarifications, wording fixes, non-semantic refinements.
4. Update of `LAST_AMENDED_DATE` and any affected templates.

All PRs MUST verify compliance via the Constitution Check in the implementation plan.
Complexity violations MUST be justified in the Complexity Tracking table of the plan.
Security violations (§3, §11) are non-waivable and have no exception path.

**Version**: 1.1.0 | **Ratified**: 2026-04-04 | **Last Amended**: 2026-04-04
