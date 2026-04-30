# Research — Spec 008 VM P2 Lifecycle

## F1 — Modify VM

### VBoxManage command

```
VBoxManage modifyvm <name> --memory <mb> --cpus <n>
```

`modifyvm` is already whitelisted. VM must be powered off.

### Decision: RAM + CPU only

Disk resize requires `VBoxManage modifymedium disk <path> --resize <mb>` and has
restrictions (cannot shrink, cannot resize if snapshots exist). Deferred to P3.

---

## F2 — Pause / Resume

### VBoxManage commands

```
VBoxManage controlvm <name> pause
VBoxManage controlvm <name> resume
```

`controlvm` is already whitelisted.

### New VMStatus value: `paused`

Currently `VBOX_STATE_MAP` maps `"paused"` → `"stopped"`. This must change:

```python
VBOX_STATE_MAP = {
    ...
    "paused": "paused",   # was "stopped"
    ...
}
```

DB constraint must be extended:
```sql
ALTER TABLE public.vms DROP CONSTRAINT vms_status_check;
ALTER TABLE public.vms ADD CONSTRAINT vms_status_check
  CHECK (status IN ('stopped','starting','running','stopping','error','paused'));
```

Frontend must add `paused` to `VM["status"]` union and STATUS_COLOR map.

---

## F3 — Save State

### VBoxManage command

```
VBoxManage controlvm <name> savestate
```

`controlvm` is already whitelisted. The command is synchronous — it returns when
the state is fully saved and the VM is powered off. After success, VirtualBox
reports the VM state as `"saved"` which already maps to `"stopped"` in our
`VBOX_STATE_MAP`. No new status needed.

### Flow

1. Assert VM is running
2. Set status → `"stopping"` in DB (shows progress to user)
3. Run `controlvm savestate`
4. On success → set status → `"stopped"` in DB
5. Log

---

## F4 — Port-Forwarding

### VBoxManage commands

```
# Add rule
VBoxManage modifyvm <name> --natpf1 "rulename,tcp,,hostport,,guestport"

# Remove rule
VBoxManage modifyvm <name> --natpf1 delete rulename
```

`modifyvm` is already whitelisted.

### Storage decision: JSONB column on `vms`

A separate `port_rules` table is cleaner but adds a join and extra migration.
For MVP, a JSONB column `nat_rules` on `vms` is sufficient and avoids N+1 queries.

```sql
ALTER TABLE public.vms
  ADD COLUMN nat_rules jsonb NOT NULL DEFAULT '[]';
```

Each rule stored as:
```json
{"name": "ssh", "protocol": "tcp", "host_port": 2222, "guest_port": 22}
```

### Validation

- Rule name: 1–50 chars, alphanumeric + hyphens
- Protocol: `tcp` or `udp`
- `host_port`: 1024–65535
- `guest_port`: 1–65535
- Uniqueness: checked in DB data before inserting

### Initial rules migration

Existing VMs have `ssh,tcp,,2222,,22` hardcoded. Their `nat_rules` will default
to `[]` after migration — the SSH rule is in VirtualBox but not in our DB. This
is acceptable for MVP: users can re-add it via the API if needed.

---

## F5 — Snapshots

### VBoxManage commands

```
# Take
VBoxManage snapshot <vm_name> take <snapshot_name> [--description <desc>]

# Restore
VBoxManage snapshot <vm_name> restore <snapshot_name>

# Delete
VBoxManage snapshot <vm_name> delete <snapshot_name>

# List (for sync)
VBoxManage snapshot <vm_name> list --machinereadable
```

### Whitelist

`snapshot` must be added to `VBOXMANAGE_COMMANDS`.

### Storage

New table `vm_snapshots` — simpler than JSONB because snapshots need their own
IDs for restore/delete operations and we list them independently.

```sql
CREATE TABLE public.vm_snapshots (
    id          uuid        NOT NULL DEFAULT gen_random_uuid(),
    vm_id       uuid        NOT NULL REFERENCES public.vms(id) ON DELETE CASCADE,
    name        text        NOT NULL,
    description text,
    created_at  timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT vm_snapshots_pkey          PRIMARY KEY (id),
    CONSTRAINT vm_snapshots_vm_name_uq    UNIQUE (vm_id, name)
);
```

### RLS

Snapshots are accessed through `vm_id`. Since the VM table already has
`user_id`-based RLS, we add matching RLS on `vm_snapshots`:

```sql
ALTER TABLE public.vm_snapshots ENABLE ROW LEVEL SECURITY;

CREATE POLICY "snapshots_user_own" ON public.vm_snapshots
  FOR ALL USING (
    EXISTS (SELECT 1 FROM public.vms WHERE id = vm_id AND user_id = auth.uid())
  );

CREATE POLICY "snapshots_admin_all" ON public.vm_snapshots
  FOR ALL USING (
    EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND is_admin = true)
  );
```

### Restore semantics

`VBoxManage snapshot <vm> restore <snapshot_name>` restores to the named snapshot.
This is destructive — the current VM disk state is replaced. We don't need to
guard against this further since the user explicitly chose a snapshot to restore.

---

## Complexity Assessment

| Feature | Effort |
|---|---|
| F1 Modify VM | ~45 min |
| F2 Pause/Resume | ~1h (new status value propagation) |
| F3 Save State | ~30 min |
| F4 Port-forwarding | ~1.5h (JSONB + validation) |
| F5 Snapshots | ~2h (new table + 3 service functions) |

**Total estimate**: ~6h split across 12 tasks — within spec but dense.
