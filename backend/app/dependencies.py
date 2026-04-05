from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer
from jose import JWTError, jwt

from app.config import settings
from app.utils.logger import logger

bearer = HTTPBearer()


async def ensure_profile_exists(user_id: str, supabase) -> None:
    result = supabase.table("profiles").select("id").eq("id", user_id).execute()
    if not result.data:
        supabase.table("profiles").insert({"id": user_id, "is_admin": False}).execute()
        logger.log(
            "auto_create_profile", user_id, "success", "Profile created via fallback"
        )


async def get_current_user(token=Depends(bearer), supabase=None) -> str:
    if supabase is None:
        from app.main import get_supabase_client

        supabase = get_supabase_client()
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
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    await ensure_profile_exists(user_id, supabase)
    return user_id
