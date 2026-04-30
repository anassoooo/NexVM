# Data Model — Spec 008 VM P2 Lifecycle

## Database migrations

### 1. Extend `vms_status_check` to include `paused`

```sql
ALTER TABLE public.vms DROP CONSTRAINT vms_status_check;
ALTER TABLE public.vms ADD CONSTRAINT vms_status_check
  CHECK (status IN ('stopped','starting','running','stopping','error','paused'));
```

### 2. Add `nat_rules` JSONB column

```sql
ALTER TABLE public.vms
  ADD COLUMN IF NOT EXISTS nat_rules jsonb NOT NULL DEFAULT '[]';
```

### 3. Create `vm_snapshots` table

```sql
CREATE TABLE IF NOT EXISTS public.vm_snapshots (
    id          uuid        NOT NULL DEFAULT gen_random_uuid(),
    vm_id       uuid        NOT NULL REFERENCES public.vms(id) ON DELETE CASCADE,
    name        text        NOT NULL,
    description text,
    created_at  timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT vm_snapshots_pkey       PRIMARY KEY (id),
    CONSTRAINT vm_snapshots_vm_name_uq UNIQUE (vm_id, name)
);

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

---

## Python changes

### `VMStatus` enum — add `paused`

```python
class VMStatus(str, Enum):
    stopped  = "stopped"
    starting = "starting"
    running  = "running"
    stopping = "stopping"
    paused   = "paused"    # NEW
    error    = "error"
```

### `LogAction` enum — 9 new values

```python
modify_vm      = "modify_vm"
pause_vm       = "pause_vm"
resume_vm      = "resume_vm"
save_state     = "save_state"
add_port_rule  = "add_port_rule"
remove_port_rule = "remove_port_rule"
take_snapshot  = "take_snapshot"
restore_snapshot = "restore_snapshot"
delete_snapshot  = "delete_snapshot"
```

### `vbox_wrapper.py` — two changes

```python
# VBOXMANAGE_COMMANDS: add
"snapshot"

# VBOX_STATE_MAP: update
"paused": "paused",  # was "stopped"
```

### New schemas

```python
class PortFwdRule(BaseModel):
    name: str
    protocol: Literal["tcp", "udp"]
    host_port: int
    guest_port: int

class VMResponse(BaseModel):
    ...
    nat_rules: list[PortFwdRule]    # NEW (from JSONB column)

class VMModifyRequest(BaseModel):
    vm_id: uuid.UUID
    ram: int | None = Field(default=None, ge=512, le=16384)
    cpu: int | None = Field(default=None, ge=1, le=32)

    @model_validator(mode="after")
    def at_least_one_field(self) -> "VMModifyRequest":
        if self.ram is None and self.cpu is None:
            raise ValueError("At least one of ram or cpu must be provided")
        return self

class PortFwdAddRequest(BaseModel):
    vm_id: uuid.UUID
    name: str = Field(min_length=1, max_length=50)
    protocol: Literal["tcp", "udp"]
    host_port: int = Field(ge=1024, le=65535)
    guest_port: int = Field(ge=1, le=65535)

class PortFwdDeleteRequest(BaseModel):
    vm_id: uuid.UUID
    name: str = Field(min_length=1)

class SnapshotTakeRequest(BaseModel):
    vm_id: uuid.UUID
    name: str = Field(min_length=1, max_length=50)
    description: str = Field(default="", max_length=200)

class SnapshotActionRequest(BaseModel):
    vm_id: uuid.UUID
    name: str = Field(min_length=1)

class SnapshotResponse(BaseModel):
    id: uuid.UUID
    vm_id: uuid.UUID
    name: str
    description: str | None
    created_at: datetime
```

---

## Frontend changes

### `VM` interface — add `nat_rules`, `paused` status

```ts
export interface PortFwdRule {
  name: string;
  protocol: "tcp" | "udp";
  host_port: number;
  guest_port: number;
}

export interface VM {
  ...
  status: "stopped" | "starting" | "running" | "stopping" | "error" | "paused"; // add paused
  nat_rules: PortFwdRule[];   // NEW
}

export interface Snapshot {
  id: string;
  vm_id: string;
  name: string;
  description: string | null;
  created_at: string;
}
```
