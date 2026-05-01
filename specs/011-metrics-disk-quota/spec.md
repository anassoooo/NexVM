# Spec 011 — VM Metrics & Disk Quota

**Created**: 2026-05-01  
**Status**: Draft

---

## Item 11 — Métriques temps réel

### Goal
Expose host-side VM metrics (CPU load, RAM usage) via `VBoxManage metrics`.

### VBoxManage commands
```bash
VBoxManage metrics setup --period 1 --samples 1 <vmname> CPU/Load/User,RAM/Usage/Used
VBoxManage metrics query <vmname> CPU/Load/User,RAM/Usage/Used
```

### API
```
GET /api/v1/vm/metrics?vm_id=<uuid>
→ VMMetrics { cpu_percent: float|null, ram_used_mb: int|null }
Errors: 404 (vm not found), 409 (VM not running)
```

### State rule
Metrics only meaningful for running VMs — 409 if not running.

### Caveats
- First query after setup may return null (no warm-up time) — frontend handles gracefully
- RAM/Usage/Used requires VirtualBox Guest Additions for accurate guest RAM; without GA it returns host-allocated RAM
- Best-effort: null fields when VBoxManage returns no data

### Frontend
- Collapsible "Metrics" section in `vm-card.tsx`, visible only when VM is running
- Manual refresh button — no continuous polling (avoid perf overhead on many VMs)

---

## Item 12 — Quotas disque

### Goal
Cap total allocated disk across all VMs per user (currently only VM count is capped).

### Config
`VM_DISK_QUOTA_MB: int = 200000` (≈ 200 GB, configurable via `.env`)

### Enforcement
Check in `create_vm`, `clone_vm`, `import_ova`:
```
sum(disk_size for all user VMs) + new_disk_size > VM_DISK_QUOTA_MB → 409
```

### Analytics update
Add `total_disk_used_mb: int` to `UserAnalytics` and `AdminAnalytics`.  
Admin dashboard: show disk usage card.

### No DB migration needed
`disk_size` already stored in `vms` table.
