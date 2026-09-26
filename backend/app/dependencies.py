import functools
from dataclasses import dataclass
from typing import Annotated

import httpx
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt
from jose.exceptions import JWTError

from app.config import settings
from app.db import get_supabase_client


@dataclass
class UserClaims:
    """Decoded claims extracted from the Supabase JWT — no admin API call needed."""
    id: str
    email: str

bearer = HTTPBearer()


@functools.lru_cache(maxsize=1)
def _get_jwks_keys() -> list[dict]:
    url = f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json"
    resp = httpx.get(url, timeout=10)
    resp.raise_for_status()
    return resp.json().get("keys", [])


def _decode_jwt(token_str: str) -> dict:
    header = jwt.get_unverified_header(token_str)
    algorithm = header.get("alg")

    if algorithm not in ("ES256", "RS256"):
        raise JWTError("Unsupported JWT algorithm")

    key_id = header.get("kid")
    if not key_id:
        raise JWTError("JWT key ID is missing")

    keys = _get_jwks_keys()
    key_data = next(
        (key for key in keys if key.get("kid") == key_id and key.get("alg") in (None, algorithm)),
        None,
    )
    if key_data is None:
        # A key may have rotated since the JWKS response was cached.
        _get_jwks_keys.cache_clear()
        keys = _get_jwks_keys()
        key_data = next(
            (key for key in keys if key.get("kid") == key_id and key.get("alg") in (None, algorithm)),
            None,
        )
    if key_data is None:
        raise JWTError("JWT signing key not found")

    return jwt.decode(
        token_str,
        key_data,
        algorithms=[algorithm],
        audience="authenticated",
    )


async def ensure_profile_exists(user_id: str, supabase) -> None:
    result = supabase.table("profiles").select("id").eq("id", user_id).execute()
    if not result.data:
        supabase.table("profiles").insert({"id": user_id, "is_admin": False}).execute()


async def get_current_user(
    token: Annotated[HTTPAuthorizationCredentials, Depends(bearer)],
) -> UserClaims:
    """
    Decodes the Supabase JWT and returns user_id + email.
    The email is embedded in the JWT payload — no admin API call required.
    """
    try:
        payload = _decode_jwt(token.credentials)
        user_id: str | None = payload.get("sub")
        email: str = payload.get("email") or ""
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
    except HTTPException:
        raise
    except Exception:
        # Catches JWKS fetch failures and any other decode errors.
        # Always return 401 (never 500) so the client can handle it cleanly.
        raise HTTPException(
            status_code=401, detail="Invalid or expired token"
        ) from None

    supabase = get_supabase_client()
    await ensure_profile_exists(user_id, supabase)
    return UserClaims(id=user_id, email=email)


async def get_current_admin_user(
    claims: Annotated[UserClaims, Depends(get_current_user)],
) -> UserClaims:
    supabase = get_supabase_client()
    result = supabase.table("profiles").select("is_admin").eq("id", claims.id).execute()
    is_admin = result.data and result.data[0].get("is_admin") is True
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return claims
