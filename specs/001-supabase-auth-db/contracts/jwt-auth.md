# Contract: JWT Authentication

**Branch**: `001-supabase-auth-db` | **Date**: 2026-04-04

This contract defines what every authenticated backend request must carry, what the backend validates, and what is extracted for downstream use. All other feature plans must conform to this contract — it is the single auth boundary for the entire backend.

---

## Request Contract (every authenticated endpoint)

**Header**:

```
Authorization: Bearer <access_token>
```

Where `<access_token>` is the Supabase-issued JWT obtained after successful login.

---

## JWT Claims (validated by backend)

| Claim | Type | Required | Description |
|---|---|---|---|
| `sub` | string (UUID) | YES | User ID — maps to `auth.users.id`. Extracted as `current_user_id`. |
| `aud` | string | YES | Must equal `"authenticated"` |
| `exp` | unix timestamp | YES | Must be in the future (not expired) |
| `iss` | string | YES | Must match Supabase project URL |
| `role` | string | YES | Must equal `"authenticated"` |

**Signature**: HS256, signed with `SUPABASE_JWT_SECRET`.

---

## Validation Rules

1. Token **present** — missing `Authorization` header → HTTP 401
2. Token **not expired** (`exp` in future) — expired token → HTTP 401 `"Invalid or expired token"`
3. Token **signature valid** (HS256 with `SUPABASE_JWT_SECRET`) — tampered token → HTTP 401
4. `aud` claim equals `"authenticated"` — wrong audience → HTTP 401
5. `sub` claim is a non-null UUID string — missing subject → HTTP 401

---

## FastAPI Dependency Signature

All protected route handlers receive `current_user_id: str` via:

```python
async def some_route(current_user_id: str = Depends(get_current_user)):
    ...
```

The `get_current_user` dependency (in `app/dependencies.py`):
- Validates all claims above
- Runs the profile fallback (`ensure_profile_exists`)
- Returns the `sub` claim value (user UUID string)
- Raises `HTTPException(401)` on any validation failure

---

## Error Responses

| Scenario | HTTP Status | Response Body |
|---|---|---|
| Missing Authorization header | 401 | `{"detail": "Not authenticated"}` |
| Invalid or tampered token | 401 | `{"detail": "Invalid or expired token"}` |
| Expired token | 401 | `{"detail": "Invalid or expired token"}` |
| Wrong audience | 401 | `{"detail": "Invalid or expired token"}` |

---

## Admin Check Contract

Admin status is **not** embedded in the JWT. It is checked at the data layer via RLS policy:

```sql
EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND is_admin = true)
```

Backend routes that require admin access additionally query:

```python
profile = supabase.table("profiles").select("is_admin").eq("id", current_user_id).single().execute()
if not profile.data or not profile.data["is_admin"]:
    raise HTTPException(status_code=403, detail="Admin access required")
```

**Rationale**: Keeping admin status out of the JWT means changes take effect immediately without requiring token re-issuance.

---

## Session Lifetime

| Property | Value |
|---|---|
| Access token lifetime | 1 hour (auto-refreshed by frontend SDK) |
| Refresh token lifetime | 24 hours from login |
| Concurrent sessions | Permitted — each login issues independent tokens |
| Logout scope | Current device only (revokes current refresh token) |

After 24 hours from login, the refresh token expires. The frontend SDK cannot renew the access token. The next request returns 401 and the user is redirected to `/login`.
