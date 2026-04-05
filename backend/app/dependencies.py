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
