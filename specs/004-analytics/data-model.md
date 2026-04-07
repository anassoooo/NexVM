# Data Model: Analytics

**Branch**: `004-analytics` | **Date**: 2026-04-07

No new database tables or migrations are required. All analytics data is read from existing tables.

---

## Existing Tables Used (Read-Only)

### `vms` (from spec 002)

| Column  | Type | Notes                                              |
|---------|------|----------------------------------------------------|
| id      | uuid | PK                                                 |
| user_id | uuid | FK → auth.users — used to scope user analytics     |
| status  | text | `stopped`, `starting`, `running`, `stopping`, `error` — counted by value |

**Queries**:
- User analytics: `SELECT status FROM vms WHERE user_id = <user_id>`
- Admin analytics: `SELECT status FROM vms`

---

### `ai_usage` (from spec 001)

| Column  | Type | Notes                                          |
|---------|------|------------------------------------------------|
| id      | uuid | PK — counted for total command count           |
| user_id | uuid | FK → auth.users — used to scope user analytics |

**Queries**:
- User analytics: `SELECT id FROM ai_usage WHERE user_id = <user_id>`
- Admin analytics: `SELECT id FROM ai_usage`

---

### `profiles` (from spec 001)

| Column | Type | Notes                            |
|--------|------|----------------------------------|
| id     | uuid | PK — counted for total user count |

**Queries**:
- Admin analytics: `SELECT id FROM profiles`

---

## Pydantic Schemas (backend)

```python
class UserAnalytics(BaseModel):
    total_vms: int
    running_vms: int
    stopped_vms: int
    error_vms: int
    total_ai_commands: int

class AdminAnalytics(BaseModel):
    total_users: int
    total_vms: int
    running_vms: int
    stopped_vms: int
    error_vms: int
    total_ai_commands: int
```

---

## TypeScript Types (frontend)

```typescript
interface UserAnalytics {
  total_vms: number;
  running_vms: number;
  stopped_vms: number;
  error_vms: number;
  total_ai_commands: number;
}

interface AdminAnalytics {
  total_users: number;
  total_vms: number;
  running_vms: number;
  stopped_vms: number;
  error_vms: number;
  total_ai_commands: number;
}
```

---

## Data Flow

```
GET /api/v1/analytics
    │
    ▼
get_current_user(token) → user_id
    │
    ▼
get_user_analytics(user_id)
  ├─ SELECT status FROM vms WHERE user_id = <user_id>
  │    → count rows by status value in Python
  └─ SELECT id FROM ai_usage WHERE user_id = <user_id>
       → len(result.data) = total_ai_commands
    │
    ▼
UserAnalytics(total_vms, running_vms, stopped_vms, error_vms, total_ai_commands)


GET /api/v1/analytics/admin
    │
    ▼
get_current_admin_user(token) → user_id (403 if not admin)
    │
    ▼
get_admin_analytics()
  ├─ SELECT id FROM profiles
  │    → len(result.data) = total_users
  ├─ SELECT status FROM vms
  │    → count rows by status value in Python
  └─ SELECT id FROM ai_usage
       → len(result.data) = total_ai_commands
    │
    ▼
AdminAnalytics(total_users, total_vms, running_vms, stopped_vms, error_vms, total_ai_commands)
```
