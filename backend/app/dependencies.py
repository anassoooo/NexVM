from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.config import settings
from app.db import get_supabase_client

bearer = HTTPBearer()


async def ensure_profile_exists(user_id: str, supabase) -> None:
    result = supabase.table("profiles").select("id").eq("id", user_id).execute()
    if not result.data:
        supabase.table("profiles").insert({"id": user_id, "is_admin": False}).execute()


async def get_current_user(
    token: Annotated[HTTPAuthorizationCredentials, Depends(bearer)],
) -> str:
    try:
        payload = jwt.decode(
            token.credentials,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
        )
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
    except JWTError:
        raise HTTPException(
            status_code=401, detail="Invalid or expired token"
        ) from None

    supabase = get_supabase_client()
    await ensure_profile_exists(user_id, supabase)
    return user_id


async def get_current_admin_user(
    user_id: Annotated[str, Depends(get_current_user)],
) -> str:
    supabase = get_supabase_client()
    result = supabase.table("profiles").select("is_admin").eq("id", user_id).execute()
    is_admin = result.data and result.data[0].get("is_admin") is True
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user_id
