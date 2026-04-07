from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies import get_current_admin_user, get_current_user
from app.models.schemas import AdminAnalytics, UserAnalytics
from app.services import analytics_service

router = APIRouter()


@router.get("/", response_model=UserAnalytics)
def get_user_analytics(
    user_id: Annotated[str, Depends(get_current_user)],
) -> UserAnalytics:
    return analytics_service.get_user_analytics(user_id)


@router.get("/admin", response_model=AdminAnalytics)
def get_admin_analytics(
    _: Annotated[str, Depends(get_current_admin_user)],
) -> AdminAnalytics:
    return analytics_service.get_admin_analytics()
