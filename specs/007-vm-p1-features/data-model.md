# Data Model — Spec 007 VM P1 Features

## Database migration

### `vms` table — add three columns

```sql
ALTER TABLE public.vms
  ADD COLUMN IF NOT EXISTS iso_path     text,
  ADD COLUMN IF NOT EXISTS vrde_enabled boolean NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS vrde_port    integer;

ALTER TABLE public.vms
  ADD CONSTRAINT vms_vrde_port_check CHECK (vrde_port IS NULL OR (vrde_port >= 1024 AND vrde_port <= 65535));
```

No new tables. No RLS changes (existing policies cover all columns).

---

## Python schema changes

### `VMResponse` — three new fields

```python
class VMResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    os: str
    ram: int
    cpu: int
    disk_size: int
    vbox_id: str | None
    status: VMStatus
    error_message: str | None
    iso_path: str | None        # NEW
    vrde_enabled: bool          # NEW
    vrde_port: int | None       # NEW
    created_at: datetime
    updated_at: datetime
```

### New request schemas

```python
class ISOAttachRequest(BaseModel):
    vm_id: uuid.UUID
    iso_path: str = Field(min_length=1)

    @field_validator("iso_path")
    @classmethod
    def validate_iso(cls, v: str) -> str:
        if not os.path.isabs(v):
            raise ValueError("iso_path must be an absolute path")
        if not v.lower().endswith(".iso"):
            raise ValueError("iso_path must end with .iso")
        return v


class ISODetachRequest(BaseModel):
    vm_id: uuid.UUID


class VRDEEnableRequest(BaseModel):
    vm_id: uuid.UUID
    port: int = Field(ge=1024, le=65535)


class VRDEDisableRequest(BaseModel):
    vm_id: uuid.UUID
```

### `LogAction` enum — four new values

```python
class LogAction(str, Enum):
    ...
    attach_iso  = "attach_iso"
    detach_iso  = "detach_iso"
    enable_vrde = "enable_vrde"
    disable_vrde = "disable_vrde"
```

---

## Frontend type changes

### `VM` interface — three new fields

```ts
export interface VM {
  ...
  iso_path: string | null;   // NEW
  vrde_enabled: boolean;     // NEW
  vrde_port: number | null;  // NEW
}
```
