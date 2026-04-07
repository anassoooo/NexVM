# Data Model: AI Command Processing

**Branch**: `003-ai-command-processing` | **Date**: 2026-04-07

No new database tables or migrations are required. The `ai_usage` and `logs` tables from spec 001 are the complete persistence layer for this feature.

---

## Existing Tables Used

### `ai_usage` (from spec 001)

| Column     | Type        | Constraints              | Notes                                     |
|------------|-------------|--------------------------|-------------------------------------------|
| id         | uuid        | PK, default gen_random_uuid() |                                      |
| user_id    | uuid        | FK → auth.users ON DELETE SET NULL | Nullable for data retention      |
| prompt     | text        | NOT NULL                 | The raw user input                        |
| response   | text        | NOT NULL                 | The raw Groq JSON response (or error text)|
| tokens     | integer     | NOT NULL                 | Total tokens from `usage.total_tokens`    |
| created_at | timestamptz | NOT NULL, default now()  |                                           |

**RLS Policies**:
- `ai_usage_user_own`: `FOR ALL USING (auth.uid() = user_id)` — users see only their own records
- `ai_usage_admin_all`: `FOR ALL USING (profiles.is_admin = true)` — admins see all records

**Index**: `ai_usage_user_id_idx ON ai_usage (user_id)`

---

### `logs` (from spec 001, reused)

All AI commands produce a log entry with `action = 'ai_command'`. The `target` field carries the VM UUID (for actions on an existing VM) or the literal string `"ai"` (for create_vm, validation failures, Groq errors).

---

## Pydantic Schemas (backend)

### Request/Response (API boundary)

```python
class AICommandRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=500)

class AICommandResponse(BaseModel):
    action: str                    # e.g. "create_vm"
    result: str                    # human-readable result, e.g. "Created VM 'ubuntu-vm'"
    ai_response: dict[str, Any]    # the validated + serialized AI action dict
```

### Internal Validation Schemas (not in API response)

```python
class AICreateVM(BaseModel):
    action: Literal["create_vm"]
    name: str = Field(min_length=1, max_length=50)   # same regex as VMCreate
    os: str = Field(min_length=1)
    ram: int = Field(ge=512, le=16384)

class AIStartVM(BaseModel):
    action: Literal["start_vm"]
    vm_id: uuid.UUID

class AIStopVM(BaseModel):
    action: Literal["stop_vm"]
    vm_id: uuid.UUID

class AIDeleteVM(BaseModel):
    action: Literal["delete_vm"]
    vm_id: uuid.UUID
```

All four use `model_dump(mode="json")` to produce JSON-serializable dicts (UUIDs → strings).

---

## TypeScript Types (frontend)

```typescript
// Existing (types/index.ts)
interface AIUsage {
  id: string;
  user_id: string | null;
  prompt: string;
  response: string;
  tokens: number;
  created_at: string;
}

// Added in this spec
interface AICommandResponse {
  action: string;
  result: string;
  ai_response: Record<string, unknown>;
}
```

---

## Data Flow

```
User prompt (string, 1-500 chars)
    │
    ▼
AICommandRequest (Pydantic, API boundary)
    │
    ▼
_check_rate_limit(user_id)
    │
    ▼
_build_system_prompt(user_id)
  └─ list_vms(user_id) → [VMResponse, ...]
  └─ JSON-serialize to inject into SYSTEM_PROMPT template
    │
    ▼
_call_groq(system_prompt, user_prompt)
  └─ returns (raw_text: str, tokens: int)
    │
    ▼
_validate_ai_response(raw_text)
  └─ json.loads() → dict
  └─ action whitelist check
  └─ Pydantic model_validate()
  └─ model_dump(mode="json") → validated: dict
    │
    ▼
_execute_action(validated, user_id)
  └─ dispatches to vm_service.create_vm / start_vm / stop_vm / delete_vm
  └─ returns result_message: str
    │
    ▼
_log_ai_usage(user_id, prompt, raw_text, tokens)  → ai_usage table
_log_action(user_id, target, LogStatus.success, result_message)  → logs table
    │
    ▼
AICommandResponse(action, result, ai_response)
```

On any failure (validation error, Groq error, VM service error):
- `_log_ai_usage` is still called (with raw error response)
- `_log_action` is called with `LogStatus.failure`
- Original HTTPException is re-raised
