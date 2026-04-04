# Research: Supabase Auth & Database Setup

**Branch**: `001-supabase-auth-db` | **Date**: 2026-04-04

---

## 1. JWT Verification in FastAPI

**Decision**: Use `python-jose[cryptography]` to decode and verify Supabase-issued JWTs server-side using the project's JWT secret.

**Rationale**: Supabase issues standard HS256 JWTs signed with the project's JWT secret (available as `SUPABASE_JWT_SECRET` in project settings). `python-jose` decodes and verifies the signature without a network call, keeping auth middleware fast (< 100ms). The `sub` claim holds the user UUID, which maps directly to `auth.users.id`.

**Implementation pattern**:

```python
# dependencies.py
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer

bearer = HTTPBearer()

async def get_current_user(token = Depends(bearer)) -> str:
    try:
        payload = jwt.decode(
            token.credentials,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated"
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    # Profile fallback (FR-003): create profile if missing
    await ensure_profile_exists(user_id)
    return user_id
```

**Alternatives considered**:
- Supabase Admin SDK (`supabase.auth.get_user(token)`) — makes a network call to Supabase on every request, adds latency and a hard dependency on Supabase availability. Rejected.
- Custom JWKS endpoint verification — overcomplicated for HS256. Rejected.

---

## 2. Auto-Profile Creation: Trigger + Login Fallback

**Decision**: Primary creation via PostgreSQL trigger on `auth.users` INSERT. Fallback via `ensure_profile_exists()` called in `get_current_user()` on every authenticated request.

**Rationale**: The trigger handles the happy path (99% of cases). The fallback handles transient trigger failures without requiring manual intervention or blocking user access (FR-003 clarification: retry on next login).

**Trigger implementation**:

```sql
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger AS $$
BEGIN
  INSERT INTO public.profiles (id, is_admin)
  VALUES (NEW.id, false)
  ON CONFLICT (id) DO NOTHING;  -- idempotent: safe if trigger fires twice
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();
```

**Fallback implementation**:

```python
async def ensure_profile_exists(user_id: str):
    result = supabase.table("profiles").select("id").eq("id", user_id).execute()
    if not result.data:
        supabase.table("profiles").insert({"id": user_id, "is_admin": False}).execute()
```

**ON CONFLICT DO NOTHING** makes the trigger and the fallback both idempotent — neither will error if the other already ran.

---

## 3. Supabase Auth Configuration (Rate Limiting & Password Policy)

**Decision**: Configure natively in Supabase Auth dashboard — no custom middleware needed.

**Supabase Auth built-in settings** (configured in Dashboard → Authentication → Settings):

| Setting | Value | Maps to |
|---|---|---|
| JWT expiry | 86400 (24 hours) | SC-003: 24-hour session |
| Minimum password length | 8 | FR-017: min 8 chars |
| Password requirement | Contains a number | FR-017: at least one number |
| Rate limit (email sign-in) | 10 per 15 minutes | FR-016: lockout after 10 attempts |

**Rationale**: All three requirements (session expiry, password policy, rate limiting) map directly to Supabase Auth configuration knobs. No custom implementation needed for MVP — this keeps the codebase minimal (§V YAGNI). The lockout message is returned automatically by Supabase as a 429 HTTP response with a `Retry-After` header; the frontend reads this and shows the user when to retry.

**Alternative considered**: Custom rate-limiting middleware in FastAPI (e.g., `slowapi`) — unnecessary since the frontend sends auth requests directly to Supabase Auth, not through the FastAPI backend. Rejected.

---

## 4. Row Level Security (RLS) Patterns

**Decision**: Enable RLS on all three application tables (`profiles`, `vms`, `logs`, `ai_usage`). Two-policy pattern per table: user-scoped + admin-override.

**Rationale**: RLS enforces data isolation at the database layer (not just the API layer), satisfying FR-008 and SC-004. The admin override uses a subquery against `profiles.is_admin` rather than a custom JWT claim, keeping the admin mechanism simple and avoiding JWT re-issuance when admin status changes.

**Policy pattern**:

```sql
-- User sees only their own rows
CREATE POLICY "user_own_rows" ON <table>
  FOR ALL USING (auth.uid() = user_id);

-- Admin sees all rows
CREATE POLICY "admin_all_rows" ON <table>
  FOR ALL USING (
    EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND is_admin = true)
  );
```

**Exception**: `profiles` table uses `id` instead of `user_id` as the ownership column.

---

## 5. Session Management in Next.js 14 App Router

**Decision**: Use `@supabase/ssr` package with `createServerClient` (server components/actions) and `createBrowserClient` (client components). Store session in cookies via middleware.

**Rationale**: `@supabase/ssr` is the official Supabase package for Next.js 14 App Router. It handles cookie-based session storage, automatic token refresh (within the 24-hour window), and SSR-compatible auth state. The `middleware.ts` reads the session cookie and redirects unauthenticated users before the page renders.

**Middleware pattern**:

```typescript
// middleware.ts
import { createServerClient } from '@supabase/ssr'
import { NextResponse } from 'next/server'

export async function middleware(request) {
  const supabase = createServerClient(...)
  const { data: { session } } = await supabase.auth.getSession()
  
  const isAuthRoute = request.nextUrl.pathname.startsWith('/login') || 
                      request.nextUrl.pathname.startsWith('/signup')
  
  if (!session && !isAuthRoute) {
    return NextResponse.redirect(new URL('/login', request.url))
  }
  return NextResponse.next()
}
```

**24-hour expiry behavior**: Supabase issues a short-lived access token (1 hour default, configurable) plus a refresh token valid for 24 hours. `@supabase/ssr` automatically refreshes the access token using the refresh token within the 24-hour window. After 24 hours, the refresh token itself expires and the user must re-authenticate. This satisfies FR-005 exactly.

**Concurrent sessions**: Supabase Auth issues independent refresh tokens per login. Each device/browser has its own token pair. Logout invalidates only that device's token (calls `supabase.auth.signOut()` which revokes only the current session's refresh token). This satisfies FR-006a with no additional implementation.

---

## 6. Database Constraint Enforcement

**Decision**: Enforce VM status and RAM constraints at the PostgreSQL level using CHECK constraints.

```sql
-- Status whitelist
ALTER TABLE vms ADD CONSTRAINT vms_status_check 
  CHECK (status IN ('stopped', 'starting', 'running', 'stopping', 'error'));

-- RAM range
ALTER TABLE vms ADD CONSTRAINT vms_ram_check 
  CHECK (ram >= 512 AND ram <= 16384);
```

**Rationale**: Database-level constraints (FR-013, FR-014) are the last line of defense — they enforce correctness even if the backend validation is bypassed. The CHECK constraint costs nothing at query time and provides a clear error message. Satisfies SC-005.
