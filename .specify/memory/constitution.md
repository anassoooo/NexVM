<!--
SYNC IMPACT REPORT
==================
Version change:    none → 1.0.0 (initial ratification)
Modified principles: n/a — first written version
Added sections:
  - §I  Project Identity
  - §II  Auth Before Everything
  - §III Dark Cyberpunk Design System  ← NEW (spec 005 input)
  - §IV  AI-First UX
  - §V   YAGNI / MVP Constraints
  - §VI  Architecture Boundaries (§VI.1–§VI.4)
  - §VII Data Access Rules
  - §VIII Frontend Conventions
  - §IX  Backend Conventions
  - §X   Complexity Budget
  - §XI  Security Requirements (§XI.1–§XI.3)
  - §XII Observability & Logging (§XII.1–§XII.2)
  - §XIII Governance
Removed sections: none
Templates:
  ✅ .specify/templates/constitution-template.md — created
  ✅ specs/005-cyberpunk-ui/ — created (design spec)
  ⚠ .specify/templates/plan-template.md — not yet created (no blocking dependency)
  ⚠ .specify/templates/spec-template.md — not yet created
  ⚠ .specify/templates/tasks-template.md — not yet created
Deferred TODOs: none — all placeholders resolved
-->

# myVMS Project Constitution

**Version**: 1.0.0
**Ratification Date**: 2026-04-20
**Last Amended**: 2026-04-20

---

## §I — Project Identity

myVMS is a web-based virtual machine management system. Regular users interact exclusively
through an AI chat interface; all VM operations and analytics are handled conversationally.
Admin users have a structured dashboard for system oversight. Authentication is managed
via Supabase. The backend is FastAPI (Python 3.12); the frontend is Next.js 14 (TypeScript 5.x).

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

All user-facing UI MUST conform to the myVMS dark cyberpunk design system defined below.
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

**Rationale**: A consistent premium dark aesthetic differentiates myVMS as a professional
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

- Supabase service role client is used in the backend only — never exposed to frontend.
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

- Python 3.12, FastAPI, Pydantic v2.
- All request/response schemas in `backend/app/models/schemas.py`.
- All business logic in `backend/app/services/`.
- All route handlers in `backend/app/routes/`.
- `ruff` for linting — CI MUST pass `ruff check .` with zero errors.
- `pytest` for tests — all new services MUST have corresponding test files with mocked Supabase.

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
