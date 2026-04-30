# Implementation Plan: VM Module P0 Bug Fixes

**Branch**: `004-analytics` | **Date**: 2026-04-21 | **Spec**: `specs/006-vm-p0-fixes/spec.md`

## Summary

Five runtime-blocking bugs introduced when the VM module was extended with real
VirtualBox hardware configuration. Fixes are purely surgical — no new endpoints,
no migrations, no schema additions beyond `AICreateVM`.

## Technical Context

**Language/Version**: Python 3.12 (backend)  
**Primary Dependencies**: FastAPI, Pydantic v2, supabase-py, groq  
**Storage**: Supabase (PostgreSQL) — no schema changes  
**Testing**: pytest — existing test suite must pass  
**Target Platform**: Windows 11 host running VirtualBox  
**Project Type**: Web service (FastAPI backend)  
**Performance Goals**: N/A (bug fixes only)  
**Constraints**: Zero regressions; `ruff check .` must pass  
**Scale/Scope**: 5 targeted line-level fixes

## Constitution Check

| Principle | Status | Notes |
|---|---|---|
| §II Auth Before Everything | ✅ PASS | No endpoint changes — existing auth dependencies unchanged |
| §VI.1 Separation of Concerns | ✅ PASS | Fixes are within service/route layers as required |
| §VII Data Access Rules | ✅ PASS | B1/B2 fix enforces user-scoped `list_vms` — removes data leak |
| §IX Backend Conventions | ✅ PASS | Python 3.12, Pydantic v2, ruff — no deviation |
| §XI.2 Input Validation | ✅ PASS | `AICreateVM` update uses Pydantic fields with constraints |
| §XI.3 Command Whitelist | ✅ PASS | No new VBoxManage commands |
| §XII.1 Mandatory Logging | ✅ PASS | No new operations — existing logging unaffected |
| §V YAGNI | ✅ PASS | Strictly fixing diagnosed bugs — no feature additions |

**Gate result**: ALL PASS — proceed to implementation.

## Project Structure

### Documentation (this feature)

```text
specs/006-vm-p0-fixes/
├── plan.md              ← this file
├── spec.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── ai-api.md
└── tasks.md             ← created by /speckit-tasks
```

### Source Code (files touched)

```text
backend/
├── app/
│   ├── models/
│   │   └── schemas.py          # AICreateVM: add cpu, disk_size fields
│   ├── services/
│   │   └── ai_service.py       # B1, B2, B3: list_vms user_id + create_vm fields + prompt
│   └── routes/
│       └── admin_vm.py         # B4: str(body.vm_id) on all service calls
└── .env                        # B5: add VM_STORAGE_PATH=
    .env.example                # B5: document VM_STORAGE_PATH
```

## Tasks

### T001 — Fix B1 + B2: `list_vms` user_id in ai_service.py

**File**: `backend/app/services/ai_service.py`

- Line 153: `vm_service.list_vms()` → `vm_service.list_vms(user_id)`
- Line 259: `vm_service.list_vms()` → `vm_service.list_vms(user_id)`

### T002 — Fix B3: AICreateVM schema + system prompt + execute action

**Files**: `schemas.py`, `ai_service.py`

- `AICreateVM`: add `cpu: int = Field(ge=1, le=32, default=2)` and `disk_size: int = Field(ge=5120, le=512000, default=20480)`
- `_execute_action create_vm`: pass `cpu=validated.get("cpu", 2)`, `disk_size=validated.get("disk_size", 20480)` to `VMCreate`
- `SYSTEM_PROMPT create_vm`: update format example to include optional `cpu` and `disk_size`

### T003 — Fix B4: str(body.vm_id) in admin_vm.py

**File**: `backend/app/routes/admin_vm.py`

- Wrap `body.vm_id` with `str()` on lines 19, 26, 33, 39

### T004 — Fix B5: VM_STORAGE_PATH in .env files

**Files**: `backend/.env`, `backend/.env.example`

- Add `VM_STORAGE_PATH=` with inline comment to both files

### T005 — Verify: ruff + pytest

```bash
cd backend && ruff check . && pytest
```
