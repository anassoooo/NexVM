# Tasks — Spec 012 Security Hardening

**Branch**: `012-security-hardening`
**Total tasks**: 14
**Order**: P0 first (T001–T005), then P1 (T006–T010), P2 (T011–T012), verification (T013–T014).
`[P]` = can run in parallel with the previous task (different files).

| ID | Title | Feature | Est. | Status |
|---|---|---|---|---|
| T001 | Branch + settings `ISO_DIR` / `EXPORT_DIR` | F2 | 0.5 h | pending |
| T002 | `resolve_inside()` helper + path validators | F2 | 1.5 h | pending |
| T003 | `vm_service`: address VMs by `vbox_id`, unique names, drop auto-purge | F1 | 3 h | pending |
| T004 | Tests: VM isolation | F1 | 1.5 h | pending |
| T005 | Tests: path confinement | F2 | 1 h | pending |
| T006 | [P] Remove `GET /vm/public` | F4 | 0.25 h | pending |
| T007 | Routes + dependencies `async def` → `def`; drop `ensure_profile_exists` | F3, F7 | 1.5 h | pending |
| T008 | Test: API stays responsive during slow VBoxManage call | F3 | 1 h | pending |
| T009 | AI backend: `delete_vm` → `pending_action` | F5 | 2 h | pending |
| T010 | AI frontend: Confirm / Cancel | F5 | 2 h | pending |
| T011 | [P] No default NAT rule + host-port conflict check | F6 | 1.5 h | pending |
| T012 | [P] Snapshot / port-rule name validation | F8 | 0.5 h | pending |
| T013 | Docs: `.env.example`, input placeholders, release note | F2 | 0.5 h | pending |
| T014 | Verify: ruff + pytest + tsc + lint + build + manual test | all | 1.5 h | pending |

---

## T001 — Branch + settings

- `git checkout -b 012-security-hardening` from `main`
- `config.py`: add `ISO_DIR: str = ""`, `EXPORT_DIR: str = ""`
- `vbox_wrapper.py`: `get_iso_dir()` / `get_export_dir()` returning the setting or
  `os.path.join(get_storage_base(), "isos" | "exports")`
- `main.py` lifespan: `os.makedirs` both, same error handling as the storage path

**Done when**: backend starts and logs both directories.

---

## T002 — `resolve_inside()` + path validators

```python
def resolve_inside(path: str, base: str) -> str
```

- `real = os.path.realpath(path)`, `root = os.path.realpath(base)`
- Compare with `os.path.normcase` and `os.path.commonpath`; raise `ValueError(f"Path must be inside {root}")` otherwise
- Return `real`
- `schemas.py`: `ISOAttachRequest.iso_path` → `resolve_inside(v, get_iso_dir())`;
  `OVAExportRequest.output_path` and `OVAImportRequest.source_path` → `get_export_dir()`
- Keep the existing absolute-path and extension checks
- AI `attach_iso` (`ai_service.py:355`): validate through `ISOAttachRequest` or call `resolve_inside`

**Done when**: invalid paths give 422 from the API; `ruff check .` passes.

---

## T003 — `vm_service`: VirtualBox resource isolation

- Add `_vbox_ref(vm: dict) -> str` → `vm.get("vbox_id") or vm["name"]`
- Replace every `vm["name"]` / `vm_name` passed to VBoxManage (32 uses) with `_vbox_ref(vm)`;
  keep `vm["name"]` in log and response messages
- `create_vm`: `vbox_name = f"{data.name}-{secrets.token_hex(4)}"`; use it for `createvm --name`
  and `get_vm_disk_path(vbox_name)`; use the parsed UUID for steps 2–6 and `cleanup()`;
  if the UUID can't be parsed, fail with 500 and run `cleanup()` by `vbox_name`
- `clone_vm` (line 863): `clonevm <vbox_ref> --name <new_name>-<hex>`; read the new UUID with
  `showvminfo --machinereadable` and store it in `vbox_id`
- `import_ova` (line 941): `--vmname <name>-<hex>`; store the resulting UUID
- `_run_vbox`: delete the "already exists" auto-purge block (lines ~110–135); map that error to
  HTTP 409 "A VirtualBox VM with this name already exists"

**Done when**: `grep -n 'vm\["name"\]' vm_service.py` shows only log/message uses;
existing tests pass after updating argv assertions in `test_vm_service.py`.

---

## T004 — Tests: VM isolation (`tests/test_vm_isolation.py`)

1. `create_vm` passes a `--name` matching `^<name>-[0-9a-f]{8}$`
2. Two `create_vm` calls with the same display name produce different VBox names
3. `createvm` "already exists" → HTTP 409 and no `unregistervm` call, no `shutil.rmtree`
4. `start_vm` / `stop_vm` / `delete_vm` pass `vbox_id` as the VM argument
5. `_vbox_ref` falls back to `name` when `vbox_id` is `None`

**Done when**: all 5 pass.

---

## T005 — Tests: path confinement (`tests/test_path_confinement.py`)

Use `tmp_path` as the base directory.
1. File inside base → accepted, returns realpath
2. Absolute path outside base → `ValueError`
3. `base/../x.ova` → `ValueError`
4. Sibling prefix `base-evil/x.ova` → `ValueError` (catches naive `startswith`)
5. Case-only difference on Windows → accepted
6. API: `POST /vm/export` with an outside path → 422

**Done when**: all 6 pass.

---

## T006 — Remove `GET /vm/public`

- Delete `list_all_vms_public` in `routes/vm.py`
- Keep `vm_service.list_all_vms` (used by the admin route)

**Done when**: `GET /api/v1/vm/public` is not routed; no frontend reference (already none).

---

## T007 — Sync handlers + drop per-request profile check

- `routes/{vm,admin_vm,ai,analytics,logs,schedules,auth}.py`: `async def` → `def`
- `dependencies.py`: `get_current_user`, `get_current_admin_user` → `def`; remove
  `ensure_profile_exists` and its call
- Confirm `_get_is_admin` and `get_current_admin_user` treat a missing profile as non-admin
- Leave `health.py` as is

**Done when**: `grep -rn "async def" app/routes app/dependencies.py` shows only `health_check`;
all tests pass.

---

## T008 — Test: non-blocking API (`tests/test_nonblocking.py`)

- Patch `run_vbox_command` to `time.sleep(2)`; start `POST /vm/start` in a task;
  `GET /health` must return within 0.5 s
- Use the app with auth dependency overridden

**Done when**: test passes, and fails if a route is switched back to `async def`.

---

## T009 — AI backend: pending delete

- `schemas.py`: `class PendingAction(BaseModel): action: Literal["delete_vm"]; vm_id: uuid.UUID; vm_name: str`;
  `AICommandResponse.pending_action: PendingAction | None = None`
- `ai_service._execute_action`: for `delete_vm`, `_get_vm_or_404(vm_id, user_id)` and return
  `("Delete VM '<name>'? This cannot be undone.", PendingAction(...))` — no delete
- `process_ai_command`: pass `pending_action` into the response; usage logging unchanged
- Tests in `test_ai_service.py`: delete is not called; `pending_action` is set; unknown VM → 404

**Done when**: tests pass.

---

## T010 — AI frontend: Confirm / Cancel

- `types/index.ts`: `pending_action?: { action: "delete_vm"; vm_id: string; vm_name: string } | null`
- `ai-chat.tsx`: when a bot message carries `pending_action`, render two buttons styled per §III
  (primary gradient pill for Confirm, glass outline for Cancel)
- Confirm → `api.post("/api/v1/vm/delete", { vm_id })` → append "Deleted VM '<name>'" or the error
- Cancel → append "Cancelled — nothing was deleted"
- Disable both buttons after one click

**Done when**: `tsc --noEmit` and `next lint` pass; manual check in T014.

---

## T011 — NAT port rules

- `create_vm` step 6: `--nic1 nat --nictype1 82540EM` only (drop `--natpf1 ssh,...,2222`)
- `add_port_rule`: query all VMs' `nat_rules` and `vrde_port`; if `host_port` is in use → 409
- Tests: conflict with another VM's rule → 409; with a VRDE port → 409; free port → ok

**Done when**: tests pass.

---

## T012 — Name validation

- `schemas.py`: `_ARG_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _.-]{0,49}$")`
- Apply to `SnapshotTakeRequest.name`, `SnapshotActionRequest.name`,
  `PortFwdAddRequest.name`, `PortFwdDeleteRequest.name`
- Tests: `--delete` → 422; `a,tcp,,22,,22` → 422; `snap 1` → ok

**Done when**: tests pass.

---

## T013 — Docs

- `backend/.env.example`: `ISO_DIR=`, `EXPORT_DIR=` with comments
- `vm-card.tsx` / export & import inputs: placeholders show the expected folder
- `README.md`: short "Upgrading to 012" note — set `ISO_DIR` or move ISOs; new VMs have no SSH
  forward by default (add one under Port forwarding)

---

## T014 — Verify

- `ruff check .` — zero errors
- `pytest` — baseline 102 passed + new tests, 0 failed
- `npx tsc --noEmit`, `npx next lint`, `npx next build` — pass
- Manual (needs two accounts):
  1. Both accounts create a VM named `test`; both appear in VirtualBox with different suffixes
  2. Attach an ISO from `ISO_DIR`; try one outside → error shown
  3. Export to `EXPORT_DIR`; import it back
  4. Start a clone in one tab; the dashboard keeps loading in another
  5. AI: "delete test" → Confirm/Cancel shown; Cancel keeps the VM; Confirm deletes it

**Done when**: all green; spec acceptance criteria ticked.
