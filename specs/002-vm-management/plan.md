# Implementation Plan: VM Management

**Branch**: `002-vm-management` | **Date**: 2026-04-06 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `/specs/002-vm-management/spec.md`  
**Depends on**: `001-supabase-auth-db` fully complete — auth middleware, schema, RLS, and Pydantic schemas (VMCreate, VMResponse) all in place.

---

## Summary

Build the complete VM lifecycle management layer for myVMS. This plan covers: a VirtualBox subprocess wrapper with timeout and error capture, a VM service layer implementing all CRUD operations and the state machine, a FastAPI route layer exposing six user endpoints plus admin endpoints that bypass ownership (FR-021), backend tests with mocked VBoxManage, and an admin VM list page at `/admin/vms` showing all users' VMs with full controls.

No new database tables or migrations are needed — the `vms` and `logs` tables from spec 001 are the complete persistence layer for this feature.

---

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript 5.x (frontend)  
**Primary Dependencies**: FastAPI, supabase-py, python-jose, uvicorn (backend); @supabase/ssr, Next.js 14, Tailwind CSS (frontend)  
**New Backend Files**: `vbox_wrapper.py`, `vm_service.py`, `routes/vm.py`, `routes/admin_vm.py` (+ update `main.py`)  
**New Frontend Files**: `components/vm-card.tsx`, `components/vm-list.tsx`, `app/admin/vms/page.tsx`  
**Existing Reused Files**: `dependencies.py` (`get_current_user`, `get_current_admin_user`), `models/schemas.py` (`VMCreate`, `VMResponse`), `models/enums.py` (`VMStatus`, `LogAction`)  
**Storage**: Supabase PostgreSQL — `vms` table (state tracking), `logs` table (audit trail)  
**Testing**: pytest + pytest-asyncio with `unittest.mock.patch` for VBoxManage subprocess  
**Target Platform**: Render (backend), Vercel (frontend), VirtualBox host (local)  
**Performance Goals**: VBoxManage calls complete within 30s (SC-006); DB updates before and after subprocess call  
**Constraints**: Synchronous execution only (no background tasks); 5 whitelisted VBoxManage commands; 30s timeout enforced  
**Scale/Scope**: Single-tenant, one VirtualBox host, no VM quotas

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle / Rule | Requirement | Status | Notes |
|---|---|---|---|
| §II — Auth Before Everything | All VM endpoints protected by JWT | **PASS** | All 7 endpoints use `get_current_user` dependency from spec 001 |
| §II — Admin routes check admin claim | Admin VM routes must verify `is_admin` before cross-user access | **PASS** | `/api/v1/admin/vm/*` uses `get_current_admin_user`; FR-021 bypass still enforces state rules + logging |
| §VI.1 — Schema Consistency | `vms` table used as-is from spec 001 | **PASS** | No schema changes; spec 001 contracts are read-only |
| §VI.3 — No direct frontend DB writes | Frontend calls backend API for all VM operations | **PASS** | All writes go through FastAPI service layer |
| §XI.1 — Auth Required | All 7 VM endpoints require valid JWT | **PASS** | No unauthenticated VM endpoints |
| §XI.2 — Input Validation | Pydantic validates at API boundary before VBoxManage | **PASS** | VMCreate validated before any subprocess call; name regex enforced |
| §XII.1 — Mandatory Logging | Log to `logs` table before returning response | **PASS** | All actions (including failures) logged before HTTP response |
| §V — YAGNI | No disk config, snapshots, clones, network for MVP | **PASS** | Explicitly deferred in spec clarifications |
| §Security — No shell injection | VBoxManage called via `subprocess.run(list)`, never shell=True | **PASS** | Hardcoded command map + list argument passing |

**All gates pass. No violations. Proceeding to Phase 0.**

---

## Project Structure

### Documentation (this feature)

```text
specs/002-vm-management/
├── plan.md              ✅ This file
├── research.md          ✅ Phase 0 output
├── data-model.md        ✅ Phase 1 output
├── quickstart.md        ✅ Phase 1 output
├── contracts/
│   ├── vm-api.md        ✅ Phase 1 output
│   └── vbox-commands.md ✅ Phase 1 output
├── checklists/
│   └── requirements.md  ✅ Quality gate
└── tasks.md             — Phase 2 output
```

### Source Code Changes

```text
backend/
├── app/
│   ├── main.py              MODIFY — include VM router
│   ├── models/
│   │   └── schemas.py       MODIFY — add VMActionRequest schema
│   ├── routes/
│   │   └── vm.py            CREATE — HTTP layer for all 7 VM endpoints
│   └── services/
│       ├── vbox_wrapper.py  CREATE — subprocess abstraction
│       └── vm_service.py    CREATE — all CRUD + state machine logic
└── tests/
    └── test_vm_service.py   CREATE — mocked VBoxManage tests

frontend/
├── app/
│   └── admin/
│       └── vms/
│           └── page.tsx     CREATE — admin VM list (server component, admin guard, shows all users' VMs)
└── components/
    ├── vm-card.tsx          CREATE — single VM display + action buttons (includes owner field for admin view)
    └── vm-list.tsx          CREATE — grid of VMCards + loading/empty states
```

**No database migrations required.** All tables, constraints, indexes, and RLS policies for this feature were created in `supabase/migrations/001_initial_schema.sql`.

---

## Amendment — 2026-04-20 (Clarification Session FR-001, FR-010, FR-022)

**Changes already applied to code** (zero new tasks needed):
- `vm_service.delete_vm` — accepts `"stopped" OR "error"` (FR-010 extended)
- `ai_service._build_system_prompt` — includes `error_message` in VM context (FR-020)
- `ai_service._execute_action` — post-create boot disk warning (Assumptions)
- `config.py` — `VM_QUOTA_PER_USER: int = 5` env var
- `vm_service.create_vm` — quota check before VBoxManage call (FR-001)
- Test mocks updated for quota check (3 tests)

**Still requires implementation** (Tasks T030–T033 added to Phase 9):
- `force_reset_vm(vm_id, actor_id)` — DB-only status reset (FR-022)
- Admin route `POST /api/v1/admin/vm/force-reset` (FR-022)
- Frontend "Force Reset" button on `/admin/vms` vm-card (FR-022)
- New tests: force-reset, error-state delete, quota-exceeded (coverage gap)

---

## Complexity Tracking

No constitution violations. All tasks within 4-hour complexity budget (§10.3). Synchronous subprocess execution avoids background-task complexity for MVP. Five-command whitelist avoids the need for a dynamic command builder.
