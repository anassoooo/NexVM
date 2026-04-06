# Implementation Plan: VM Management

**Branch**: `002-vm-management` | **Date**: 2026-04-06 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `/specs/002-vm-management/spec.md`  
**Depends on**: `001-supabase-auth-db` fully complete — auth middleware, schema, RLS, and Pydantic schemas (VMCreate, VMResponse) all in place.

---

## Summary

Build the complete VM lifecycle management layer for myVMS. This plan covers: a VirtualBox subprocess wrapper with timeout and error capture, a VM service layer implementing all CRUD operations and the state machine, a FastAPI route layer exposing six endpoints, backend tests with mocked VBoxManage, and a frontend VMs page with VMCard/VMList components wired to the API.

No new database tables or migrations are needed — the `vms` and `logs` tables from spec 001 are the complete persistence layer for this feature.

---

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript 5.x (frontend)  
**Primary Dependencies**: FastAPI, supabase-py, python-jose, uvicorn (backend); @supabase/ssr, Next.js 14, Tailwind CSS (frontend)  
**New Backend Files**: `vbox_wrapper.py`, `vm_service.py`, `routes/vm.py` (+ update `main.py`)  
**New Frontend Files**: `components/vm-card.tsx`, `components/vm-list.tsx`, `app/vms/page.tsx`  
**Existing Reused Files**: `dependencies.py` (`get_current_user`), `models/schemas.py` (`VMCreate`, `VMResponse`), `models/enums.py` (`VMStatus`, `LogAction`)  
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
| §II — Admin routes check admin claim | No admin-only VM endpoints in this spec | **PASS** | All users access only their own VMs; admin can see all via RLS |
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
│   └── vms/
│       └── page.tsx         CREATE — VM list page (server component)
└── components/
    ├── vm-card.tsx          CREATE — single VM display + action buttons
    └── vm-list.tsx          CREATE — grid of VMCards + loading/empty states
```

**No database migrations required.** All tables, constraints, indexes, and RLS policies for this feature were created in `supabase/migrations/001_initial_schema.sql`.

---

## Complexity Tracking

No constitution violations. All tasks within 4-hour complexity budget (§10.3). Synchronous subprocess execution avoids background-task complexity for MVP. Five-command whitelist avoids the need for a dynamic command builder.
