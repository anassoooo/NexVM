import logging

from fastapi import APIRouter, Depends, HTTPException
from supabase import AuthApiError

from app.db import get_supabase_client
from app.dependencies import get_current_user
from app.models.schemas import AuthResponse, LoginRequest, SignupRequest, SignupResponse, UserInfo

logger = logging.getLogger("myVMS.auth")
router = APIRouter()


def _get_is_admin(supabase, user_id: str) -> bool:
    result = supabase.table("profiles").select("is_admin").eq("id", user_id).execute()
    return bool(result.data and result.data[0].get("is_admin"))


@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest):
    supabase = get_supabase_client()
    try:
        res = supabase.auth.sign_in_with_password(
            {"email": body.email, "password": body.password}
        )
    except AuthApiError as e:
        logger.warning("Login failed for %s: %s", body.email, e.message)
        raise HTTPException(status_code=401, detail="Invalid email or password") from e

    if not res.session or not res.user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    logger.info("Login success: %s", body.email)
    return AuthResponse(
        access_token=res.session.access_token,
        user=UserInfo(
            id=res.user.id,
            email=res.user.email,
            is_admin=_get_is_admin(supabase, str(res.user.id)),
        ),
    )


@router.post("/signup", response_model=SignupResponse, status_code=201)
async def signup(body: SignupRequest):
    supabase = get_supabase_client()
    try:
        res = supabase.auth.sign_up(
            {"email": body.email, "password": body.password}
        )
    except AuthApiError as e:
        logger.warning("Signup failed for %s: %s", body.email, e.message)
        raise HTTPException(status_code=400, detail=e.message) from e

    if not res.user:
        raise HTTPException(status_code=400, detail="Signup failed")

    logger.info("Signup success: %s", body.email)

    user_info = UserInfo(
        id=res.user.id,
        email=res.user.email,
        is_admin=False,
    )

    # Session is None when email confirmation is required
    if res.session:
        return SignupResponse(
            message="Account created successfully",
            user=user_info,
            access_token=res.session.access_token,
        )

    return SignupResponse(
        message="Account created — please confirm your email before logging in",
        user=user_info,
    )


@router.get("/me", response_model=UserInfo)
async def get_me(user_id: str = Depends(get_current_user)):
    supabase = get_supabase_client()
    res = supabase.auth.admin.get_user_by_id(user_id)
    return UserInfo(
        id=res.user.id,
        email=res.user.email,
        is_admin=_get_is_admin(supabase, user_id),
    )
