import asyncio
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, Depends

from app.dependencies import get_current_user
from app.models.schemas import AICommandRequest, AICommandResponse
from app.services import ai_service

router = APIRouter()

_executor = ThreadPoolExecutor(max_workers=4)


@router.post("/command", response_model=AICommandResponse)
async def ai_command(
    body: AICommandRequest, current_user_id: str = Depends(get_current_user)
):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        _executor, ai_service.process_ai_command, body.prompt, current_user_id
    )
