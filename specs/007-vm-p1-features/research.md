# Research — Spec 007 VM P1 Features

## F1 — ISO / Boot Media

### VBoxManage commands

**IDE controller** — VirtualBox creates VMs without an IDE controller by default
when the SATA controller already handles the disk. We must add one explicitly:

```
VBoxManage storagectl <name> --name "IDE" --add ide --controller PIIX4
```

This is idempotent — if IDE already exists VBoxManage returns an error we must swallow.

**Attach ISO:**
```
VBoxManage storageattach <name> \
  --storagectl "IDE" --port 0 --device 0 \
  --type dvddrive --medium "<absolute_path_to.iso>"
```

**Detach ISO (replace with empty drive):**
```
VBoxManage storageattach <name> \
  --storagectl "IDE" --port 0 --device 0 \
  --type dvddrive --medium emptydrive
```

### Path validation

`iso_path` is supplied by the user. We must validate:
1. It is an absolute path (reject relative paths)
2. `os.path.exists(iso_path)` is True on the host
3. It ends with `.iso` (loose check — prevents obvious mistakes)

**Decision**: validate in the route via Pydantic `field_validator`, not in the service.

### DB

`iso_path TEXT` nullable column on `vms`. No separate table needed.
Set on attach, set to NULL on detach.

---

## F2 — VRDE Remote Access

### VBoxManage commands

**Enable VRDE (VM must be stopped):**
```
VBoxManage modifyvm <name> --vrde on --vrdeport <port>
```

**Disable VRDE:**
```
VBoxManage modifyvm <name> --vrde off
```

`modifyvm` is already in `VBOXMANAGE_COMMANDS` whitelist — no change needed.

### Port uniqueness

Before enabling VRDE, query Supabase:
```sql
SELECT id FROM vms WHERE vrde_port = <port> AND id != <vm_id>
```
If any row returned → 409 Conflict.

### DB

`vrde_enabled BOOLEAN NOT NULL DEFAULT FALSE` and `vrde_port INTEGER NULL` on `vms`.
No separate table. No index needed (low cardinality, few VMs per user).

---

## F3 — Auto-polling

### Implementation

Standard React pattern: `useEffect` + `setInterval` in the client components
(`vms-client.tsx`, `admin-vms-client.tsx`).

```ts
useEffect(() => {
  const hasTransitional = vms.some(
    (v) => v.status === "starting" || v.status === "stopping"
  );
  if (!hasTransitional) return;

  const id = setInterval(() => refetch(), 5000);
  return () => clearInterval(id);
}, [vms]);
```

The `vms` dependency triggers a re-evaluation after every refetch, so polling
stops the moment the last transitional VM resolves.

**No backend changes** — `GET /api/v1/vm` already returns current status.

### Flicker prevention

`refetch()` updates `vms` state in-place via `setVms(data)`. React batches
the re-render — no card unmount/remount, no visual flicker.

---

## Complexity Assessment

| Feature | Effort |
|---|---|
| F1 ISO attach/detach | ~2h — migration + 2 service fns + 2 routes + frontend card badge |
| F2 VRDE enable/disable | ~1.5h — migration + 2 service fns + 2 routes + frontend card badge |
| F3 Auto-polling | ~30min — pure frontend `useEffect` in 2 components |

**Total estimate**: ~4h — within §X.3 task ceiling.
