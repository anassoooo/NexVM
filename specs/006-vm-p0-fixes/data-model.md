# Data Model — Spec 006 P0 Bug Fixes

## No schema changes

No new tables, columns, or migrations are required.

## Schema changes (Python only)

### `AICreateVM` — add optional hardware fields

```python
class AICreateVM(BaseModel):
    action: Literal["create_vm"]
    name: str = Field(min_length=1, max_length=50)
    os: str = Field(min_length=1)
    ram: int = Field(ge=512, le=16384)
    cpu: int = Field(ge=1, le=32, default=2)          # NEW
    disk_size: int = Field(ge=5120, le=512000, default=20480)  # NEW
```

Both fields are **optional with sensible defaults** so the AI can omit them for
simple create requests and still produce valid `VMCreate` objects.
