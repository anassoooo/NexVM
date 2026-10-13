# Implementation Plan: Security Hardening

**Branch**: `012-security-hardening` | **Date**: 2026-10-13 | **Spec**: `specs/012-security-hardening/spec.md`

## Summary

Eight fixes from the 2026-10-13 review. P0: stop cross-user VM destruction by addressing VMs
by `vbox_id` with host-unique VirtualBox names (F1), and confine user-supplied host paths to
configured directories (F2). P1: make blocking handlers sync (F3), remove the unauthenticated
VM list (F4), require confirmation for AI deletions (F5). P2: drop the fixed SSH port (F6), the
per-request profile query (F7), and tighten CLI argument names (F8). No database migration.

## Technical Context

**Language/Version**: Python 3.12+ (backend), TypeScript 5.x (frontend)
**Primary Dependencies**: FastAPI, Pydantic v2, supabase-py 2.x, VBoxManage 7.2, Next.js 14
**Storage**: Supabase — no schema change (`vms.vbox_id` already populated for all rows)
**Testing**: pytest with mocked Supabase and `run_vbox_command`; `tsc --noEmit`; `next build`
**Baseline**: 102 passed, 3 skipped (`pytest` from `backend/`)
**Constraints**: `ruff check .`, `tsc --noEmit`, `next lint` must pass; no new dependencies

## Constitution Check

| Principle | Status | Notes |
|---|---|---|
| §II Auth Before Everything | ✅ PASS | F4 removes the only unauthenticated non-health route |
| §IV AI-First UX | ✅ PASS | F5 keeps deletion in the chat flow; adds a confirm step only |
| §V YAGNI | ✅ PASS | No new features beyond the confirm step; Redis rate limit deferred |
| §VI.1 Separation of Concerns | ✅ PASS | Path checks in schemas/service; frontend only renders `pending_action` |
| §VI.2 API Versioning | ✅ PASS | `AICommandResponse.pending_action` is additive; `/vm/public` was unused |
| §VI.3 No Direct Frontend DB Writes | ✅ PASS | Confirm uses `POST /api/v1/vm/delete` |
| §VI.4 Environment Config | ✅ PASS | `ISO_DIR`, `EXPORT_DIR` via pydantic-settings |
| §VII Data Access Rules | ✅ PASS | Ownership checks unchanged; F7 removes a write from the auth path |
| §IX Backend Conventions | ✅ PASS | F3 makes blocking handlers `def` as now required |
| §XI.2 Input Validation | ✅ PASS | F2, F8 extend Pydantic validators |
| §XI.3 Command Whitelist | ✅ PASS | No new subcommands |
| §XI.4 Host Filesystem Confinement | ✅ PASS | Implemented by F2 |
| §XI.5 VirtualBox Resource Isolation | ✅ PASS | Implemented by F1 |
| §XI.6 Destructive AI Confirmation | ✅ PASS | Implemented by F5 |
| §XI.7 CLI Argument Safety | ✅ PASS | Implemented by F8 (VM names already restricted) |
| §XII Observability & Logging | ✅ PASS | Deletion still logged by `vm_service.delete_vm`; AI proposal logged to `ai_usage` |
| §X.3 Task Ceiling | ✅ PASS | Largest task (T003) estimated at ~3 h |

**Gate result**: ALL PASS — proceed to tasks.

## Design Decisions

### D1 — Address VMs by `vbox_id` (F1)

Add `_vbox_ref(vm: dict) -> str` in `vm_service.py` returning `vm["vbox_id"] or vm["name"]`, and
replace the 32 `vm["name"]` uses that feed VBoxManage. VBoxManage accepts a UUID anywhere a VM
name is accepted. Display names in log messages stay as `vm["name"]`.

New VMs: `vbox_name = f"{data.name}-{secrets.token_hex(4)}"`. Used for `createvm --name`,
the disk path (`get_vm_disk_path(vbox_name)`), and the `clonevm --name` / `import --vsys 0
--vmname` targets. Steps 2–6 of `create_vm` use the UUID parsed from `createvm` output.

The orphan auto-purge is deleted rather than made safe: with random suffixes a collision means
something unexpected happened, and deleting files is the wrong default.

Alternative rejected: a new `vbox_name` column. Not needed — `vbox_id` is enough and avoids a
migration.

### D2 — Path confinement helper (F2)

`vbox_wrapper.py` gets `resolve_inside(path: str, base: str) -> str`:
`real = os.path.realpath(path)`; reject unless
`os.path.commonpath([real, os.path.realpath(base)]) == os.path.realpath(base)`
(case-insensitive on Windows via `os.path.normcase`). Pydantic validators call it, so invalid
paths fail with 422 before reaching the service. `lifespan` creates both directories.

### D3 — Sync handlers (F3)

Mechanical `async def` → `def` in route modules and auth dependencies. FastAPI runs sync
handlers in its thread pool (default 40 threads), which is sufficient for this app.
Tests that call handlers through `AsyncClient` keep working unchanged.

### D4 — Pending action (F5)

Backend: `_execute_action` returns `(message, pending_action)`; for `delete_vm` it verifies
ownership with `_get_vm_or_404` (so the user sees a clear error early) and returns the pending
action without deleting. Frontend: `ai-chat.tsx` renders Confirm / Cancel under a message whose
response has `pending_action`, and disables them after one click.

## Project Structure

### Source Code (files touched)

```text
backend/
├── app/
│   ├── config.py                 # ISO_DIR, EXPORT_DIR
│   ├── main.py                   # create ISO_DIR / EXPORT_DIR at startup
│   ├── dependencies.py           # sync deps, drop ensure_profile_exists
│   ├── models/schemas.py         # path validators, name regex, pending_action
│   ├── services/
│   │   ├── vbox_wrapper.py       # resolve_inside(), storage dir helpers
│   │   ├── vm_service.py         # _vbox_ref, unique names, no auto-purge,
│   │   │                         # no default natpf, host-port conflict check
│   │   └── ai_service.py         # delete_vm → pending_action
│   └── routes/                   # async def → def; remove /vm/public
├── tests/
│   ├── test_vm_isolation.py      # F1
│   ├── test_path_confinement.py  # F2
│   ├── test_nonblocking.py       # F3
│   └── (existing tests updated where they assert names or async handlers)
├── .env.example                  # ISO_DIR, EXPORT_DIR
frontend/
├── types/index.ts                # AICommandResponse.pending_action
├── components/ai-chat.tsx        # Confirm / Cancel UI
└── components/vm-card.tsx        # path input placeholders mention allowed dirs
```

## Risks

| Risk | Mitigation |
|---|---|
| Existing ISOs live outside `ISO_DIR` and stop attaching | Release note: set `ISO_DIR` in `backend/.env` to the current ISO folder, or move files |
| A VM row with null `vbox_id` | `_vbox_ref` falls back to `name`; all current rows have it |
| Tests assert exact VBoxManage argv with VM names | Update assertions to the `vbox_id` form in T003 |
| Sync handlers exhaust the thread pool under many slow calls | Acceptable for a single-host deployment; revisit if needed |

## Rollout

1. Implement on branch `012-security-hardening`; all checks green.
2. Set `ISO_DIR` / `EXPORT_DIR` in `backend/.env`.
3. Manual test: two accounts create same-named VMs; attach ISO; export; AI delete → confirm.
4. Merge to `main`.
