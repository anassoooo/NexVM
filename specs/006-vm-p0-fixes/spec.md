# Spec 006 — VM Module P0 Bug Fixes

**Branch**: `004-analytics`  
**Date**: 2026-04-21  
**Priority**: P0 — production blockers

## Overview

Five bugs introduced when the VM module was extended with real VirtualBox logic
and new hardware fields (`cpu`, `disk_size`, `vbox_id`). All cause runtime crashes
or data integrity violations.

## Bug Inventory

### B1 — `_build_system_prompt` calls `list_vms()` without `user_id`

**File**: `backend/app/services/ai_service.py:153`  
**Symptom**: `TypeError` on every AI command — `list_vms()` now requires a positional argument  
**Fix**: Pass `user_id` to `vm_service.list_vms(user_id)`

### B2 — `_execute_action` calls `list_vms()` without `user_id`

**File**: `backend/app/services/ai_service.py:259`  
**Symptom**: Same `TypeError` when AI resolves a `list_vms` action  
**Fix**: Pass `user_id` to `vm_service.list_vms(user_id)`

### B3 — AI `create_vm` action omits `cpu` and `disk_size`

**File**: `backend/app/services/ai_service.py:266`  
**Symptom**: VMs created via AI always use defaults (2 vCPU, 20 GB) regardless of user intent  
**Fix**:
- Add `cpu` and `disk_size` optional fields to `AICreateVM` schema
- Pass them in `VMCreate(...)` call in `_execute_action`
- Update system prompt to mention `cpu` and `disk_size` in `create_vm` action

### B4 — `admin_vm.py` passes `uuid.UUID` where `str` expected

**File**: `backend/app/routes/admin_vm.py:19,26,33,39`  
**Symptom**: Supabase `.eq()` filter may misbehave with UUID objects vs strings  
**Fix**: Wrap all `body.vm_id` with `str()` before passing to service functions

### B5 — `VM_STORAGE_PATH` missing from `.env`

**File**: `backend/.env`  
**Symptom**: VMs are stored in `~/VirtualBox VMs` with no explicit control;
path is undefined in production  
**Fix**: Add `VM_STORAGE_PATH=` to `.env` and `.env.example` (empty = use VBox default, set explicitly for production)

## Acceptance Criteria

- [ ] All AI commands execute without `TypeError`
- [ ] `list_vms` via AI returns only the calling user's VMs
- [ ] AI `create_vm` respects `cpu`/`disk_size` when specified in prompt
- [ ] Admin VM operations pass string IDs to service layer
- [ ] `VM_STORAGE_PATH` is documented in `.env.example`
- [ ] `ruff check .` passes with zero errors
- [ ] Existing tests pass
