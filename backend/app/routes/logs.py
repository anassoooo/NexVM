from typing import Annotated

from fastapi import APIRouter, Depends

from app.db import get_supabase_client
from app.dependencies import get_current_user
from app.models.schemas import AIUsageResponse, LogResponse

router = APIRouter()

_LIMIT = 100


@router.get("/", response_model=list[LogResponse])
def get_user_logs(
    user_id: Annotated[str, Depends(get_current_user)],
) -> list[LogResponse]:
    sb = get_supabase_client()
    result = (
        sb.table("logs")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(_LIMIT)
        .execute()
    )
    return [LogResponse(**row) for row in result.data]


@router.get("/ai-usage", response_model=list[AIUsageResponse])
def get_user_ai_usage(
    user_id: Annotated[str, Depends(get_current_user)],
) -> list[AIUsageResponse]:
    sb = get_supabase_client()
    result = (
        sb.table("ai_usage")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(_LIMIT)
        .execute()
    )
    return [AIUsageResponse(**row) for row in result.data]
