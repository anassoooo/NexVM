from fastapi import APIRouter, Depends

from app.dependencies import UserClaims, get_current_user
from app.models.schemas import AICommandRequest, AICommandResponse
from app.services import ai_service

router = APIRouter()


@router.post("/command", response_model=AICommandResponse)
def ai_command(
    body: AICommandRequest, claims: UserClaims = Depends(get_current_user)
):
    return ai_service.process_ai_command(body.prompt, claims.id)
