<!--
SYNC IMPACT REPORT
==================
Version change:    1.0.0 → 1.1.0 (MINOR — new security principles, project rename)
Modified principles:
  - §I   Project Identity — NexVM renamed to NexVM; Python 3.12+
  - §VII Data Access Rules — secret key replaces service role; shared-client rule;
         Data API grant rule; migrations-only schema changes
  - §IX  Backend Conventions — blocking I/O handlers MUST be sync `def`
Added sections:
  - §XI.4 Host Filesystem Confinement
  - §XI.5 VirtualBox Resource Isolation
  - §XI.6 Destructive AI Actions Require Confirmation
  - §XI.7 CLI Argument Safety
Removed sections: none
Templates:
  ⚠ .specify/templates/* — not restored (deleted in 696a23e); no blocking dependency
Dependent specs:
  ✅ specs/012-security-hardening/ — created to bring the codebase into compliance
Known discrepancies (not amended, needs owner decision):
  ⚠ §IV says /vms is admin-only; the current app routes regular users to /vms
Deferred TODOs: none
-->

# NexVM Project Constitution

**Version**: 1.1.0
**Ratification Date**: 2026-04-20
**Last Amended**: 2026-10-13

---

## §I — Project Identity

NexVM is a web-based virtual machine management system. Regular users interact exclusively
through an AI chat interface; all VM operations and analytics are handled conversationally.
Admin users have a structured dashboard for system oversight. Authentication is managed
via Supabase. The backend is FastAPI (Python 3.12+); the frontend is Next.js 14 (TypeScript 5.x).

---

## §II — Auth Before Everything

Every API endpoint MUST require Supabase JWT authentication. Admin-only endpoints MUST use
the `get_current_admin_user` dependency — no manual role checks inline. The single exception
is `GET /api/v1/health`. Frontend pages requiring auth MUST redirect unauthenticated users
to `/login` — no client-side-only guards.

**Rationale**: Auth failures discovered after deployment cost far more than auth gates built
from the start. Every surface must be covered by default; exceptions require explicit justification.

---

## §III — Dark Cyberpunk Design System

All user-facing UI MUST conform to the NexVM dark cyberpunk design system defined below.
No component SHOULD deviate from these tokens without a constitution amendment.

### Color Palette

| Token | Value | Usage |
|---|---|---|
| `--bg` | `#0a0f0d` | Page background |
| `--surface` | `rgba(255,255,255,0.04)` | Cards, panels |
| `--border` | `rgba(0,255,128,0.12)` | Card borders (1px) |
| `--accent` | `#00e676` | Primary neon green |
| `--success` | `#00c853` | Active/running state, user chat bubble |
| `--warning` | `#ff6d00` | Stopped/warning state |
| `--text-muted` | `#7a9e8a` | Secondary text, placeholders |
| `--text` | `#e8f5e9` | Primary white text |

### Visual Style

- Cards MUST use glassmorphism: `backdrop-filter: blur(16px)` + `1px solid var(--border)`.
- Key UI elements MUST have ambient glow: `box-shadow: 0 0 40px rgba(0,230,118,0.15)`.
- Every full-page background MUST include floating decorative icons (lock, gear, cloud SVG)
  at `opacity: 0.08` — purely decorative, `aria-hidden="true"`.
- Page backgrounds MUST use SVG blob / wave shapes or CSS radial gradients in `#00e676`
  at very low opacity to create depth.

### Typography

- Font family: `'Space Grotesk'` primary, `'Inter'` fallback, then system sans-serif.
- Headings: `font-weight: 700`, color `var(--text)`.
- Body: color `var(--text-muted)` for secondary content.
- Status labels: `var(--success)` for active/running, `var(--warning)` for stopped/error.

### Component Standards

| Component | Specification |
|---|---|
| User chat bubble | Green pill background `var(--success)`, right-aligned, white bold text |
| Bot chat bubble | Glass card (`var(--surface)` + border), left-aligned, `var(--text)` |
| Input field | Dark background, no border by default; `border-bottom: 2px solid var(--accent)` on focus |
| Primary button | Gradient `var(--success) → var(--accent)`, pill-shaped (`border-radius: 9999px`), bold white label |
| Status indicator | Colored text label — no badge/chip. Green = active, orange = stopped |
| VM card | Glass card with glow on hover, status indicator top-right as colored text |
| Nav bar | Dark `var(--bg)` with `border-bottom: 1px solid var(--border)`, glassmorphism on scroll |

**Rationale**: A consistent premium dark aesthetic differentiates NexVM as a professional
ops tool. Glassmorphism + neon-green accent creates a futuristic monitoring feel.

---

## §IV — AI-First UX

Regular users MUST interact exclusively through the AI chat interface (`/ai`).
There is no `/dashboard` stat card page for regular users. All VM operations
(create, start, stop, delete) and analytics queries are handled through the AI assistant.
The AI MUST open every chat session with a VM status summary (total, running, stopped, errors).
The `/vms` route is admin-accessible only for direct management.

**Rationale**: Single-surface UX reduces cognitive load. All actions go through one interface.

---

## §V — YAGNI / MVP Constraints

Features MUST NOT be added beyond the current spec. Prohibited without explicit spec approval:
caching layers, charting/animation libraries, time-range filters, paginated analytics,
premature component abstractions, feature flags, or backwards-compatibility shims.
A task is complete when acceptance criteria pass — not when it is maximally general.

---

## §VI — Architecture Boundaries

### §VI.1 — Separation of Concerns

The FastAPI backend owns ALL business logic. The Next.js frontend MUST NOT contain
business logic beyond UI state management and form validation UX.

### §VI.2 — API Versioning

All backend API routes MUST be prefixed `/api/v1/`. Future breaking changes require a new
version prefix — never mutate existing versioned routes in a breaking way.

### §VI.3 — No Direct Frontend DB Writes

The frontend MUST NOT write to Supabase directly. All mutations MUST go through the
FastAPI backend API. Read-only Supabase calls from server components are permitted
only for auth session retrieval.

### §VI.4 — Environment Config

Secrets MUST be stored in `.env` files (never hardcoded). Backend uses `pydantic-settings`.
Frontend exposes only `NEXT_PUBLIC_` prefixed vars to the browser — all secrets remain
server-side only.

---

## §VII — Data Access Rules

- The Supabase secret key (`SUPABASE_SECRET_KEY`) is used in the backend only — never exposed
  to the frontend.
- The shared backend Supabase client MUST NOT hold a user session. Sign-in and sign-up MUST
  use a short-lived client (`app.db.new_auth_client`) so database calls always run with the
  secret key.
- The `anon` and `authenticated` database roles MUST NOT have write grants on `public` tables.
  All writes go through the backend.
- Schema and grant changes MUST be made through files in `supabase/migrations/` and applied
  so they appear in the project's migration history — never ad hoc in the SQL editor.
- User-scoped queries MUST filter by `user_id` — users MUST NOT be able to read or modify
  another user's data.
- Admin analytics aggregate across all users — no `user_id` filter on admin endpoints.
- Backend MUST use Supabase client table methods only — no raw SQL strings.

---

## §VIII — Frontend Conventions

- TypeScript strict mode is required — `any` type is prohibited without explicit `// eslint-disable` justification.
- All pages live in `app/` directory (Next.js App Router). No `pages/` directory.
- Client components MUST be marked `"use client"` at the top of the file.
- Server components fetch data via Supabase SSR client; client components use browser client.
- Tailwind CSS for styling. Custom design tokens defined in `tailwind.config` and `globals.css`.
- No new third-party UI component libraries without spec approval (shadcn/ui excluded if already present).

---

## §IX — Backend Conventions

- Python 3.12+, FastAPI, Pydantic v2.
- All request/response schemas in `backend/app/models/schemas.py`.
- All business logic in `backend/app/services/`.
- All route handlers in `backend/app/routes/`.
- `ruff` for linting — CI MUST pass `ruff check .` with zero errors.
- `pytest` for tests — all new services MUST have corresponding test files with mocked Supabase.
- Route handlers and dependencies that call blocking code (VBoxManage subprocesses, the
  synchronous Supabase client, the Groq SDK) MUST be declared with `def`, not `async def`, so
  FastAPI runs them in its thread pool instead of blocking the event loop.

---

## §X — Complexity Budget

### §X.3 — Task Ceiling

No single implementation task SHOULD exceed 4 hours. Tasks estimated beyond this MUST be
decomposed into smaller sub-tasks before work begins. This applies to both backend and frontend work.

---

## §XI — Security Requirements

### §XI.1 — Auth Required

All endpoints except `GET /api/v1/health` MUST require a valid Supabase JWT.
Missing or invalid tokens MUST return HTTP 401 or 403 — never silently succeed.

### §XI.2 — Input Validation

All user-supplied input (request body, query params, path params) MUST be validated
via Pydantic schemas before any processing occurs. Validation errors return HTTP 422.

### §XI.3 — Command Whitelist

VBoxManage commands executed by the backend MUST be validated against the
`VBOXMANAGE_COMMANDS` whitelist set before execution. Arbitrary command injection
via user input is prohibited at the service layer.

### §XI.4 — Host Filesystem Confinement

User-supplied host paths (ISO files, OVA export targets, OVA import sources) MUST resolve —
after following symlinks and `..` — inside a directory configured in settings (`ISO_DIR`,
`EXPORT_DIR`). Paths outside it MUST be rejected with HTTP 422 before any VBoxManage call.
Files one user creates on the host (OVA exports) MUST live in a per-user subfolder that other
users cannot name.

### §XI.5 — VirtualBox Resource Isolation

VirtualBox names are global on the host, so a VM's user-facing name MUST NOT be used to address
it in VBoxManage. After creation, every VBoxManage call MUST address the VM by its stored
`vbox_id` UUID. New VMs (create, clone, import) MUST be registered under a host-unique name
derived from the user's name plus a random suffix. The backend MUST NOT unregister, delete or
modify a VirtualBox VM or its files unless it is the `vbox_id` of a database row owned by the
acting user (or the actor is an admin).

### §XI.6 — Destructive AI Actions Require Confirmation

The AI assistant MUST NOT execute irreversible actions (delete VM) directly from model output.
It MUST return a pending action that the user confirms in the UI; the confirmation executes
through the regular authenticated REST endpoint.

### §XI.7 — CLI Argument Safety

User-supplied values passed as VBoxManage arguments (VM, snapshot and port-rule names) MUST
match `^[A-Za-z0-9][A-Za-z0-9 _.-]*$` — in particular they MUST NOT start with `-`, so they
can never be parsed as options.

---

## §XII — Observability & Logging

### §XII.1 — Mandatory Logging

All state-changing operations (create VM, start VM, stop VM, delete VM, AI command execution)
MUST be logged to the `logs` table with: `action`, `target`, `status` (success/failure),
and `message`. Read-only operations (GET analytics, list VMs) do NOT require audit logging.

### §XII.2 — AI Usage Tracking

All AI assistant interactions MUST be inserted into the `ai_usage` table with:
`user_id`, `prompt`, `response`, and `tokens`. This applies regardless of success or failure.

---

## §XIII — Governance

**Amendment Procedure**: Any principle addition, modification, or removal MUST update this
file and bump the version. All dependent spec plan files that include a "Constitution Check"
table MUST be reviewed for continued compliance after amendment.

**Versioning Policy**:
- `MAJOR` — backward-incompatible: existing principle removed or fundamentally redefined.
- `MINOR` — additive: new section or material expansion of existing principle.
- `PATCH` — non-semantic: wording clarification, typo fix, formatting change.

**Compliance Gate**: Every feature plan (`specs/*/plan.md`) MUST include a
"Constitution Check" table validating relevant principles before implementation begins.
A plan with failing gates MUST NOT proceed to the tasks phase.

**Compliance Review**: Constitution compliance is verified at plan-creation time.
No automated enforcement exists — the reviewing author is accountable for accuracy.
