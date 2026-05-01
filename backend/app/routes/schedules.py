import uuid as uuid_lib

from fastapi import APIRouter, Depends

from app.dependencies import get_current_user
from app.models.schemas import ScheduleCreate, ScheduleResponse
from app.services import schedule_service

router = APIRouter()


@router.get("/", response_model=list[ScheduleResponse])
async def list_schedules(current_user_id: str = Depends(get_current_user)):
    return schedule_service.list_schedules(current_user_id)


@router.get("/{vm_id}", response_model=list[ScheduleResponse])
async def list_schedules_for_vm(
    vm_id: uuid_lib.UUID, current_user_id: str = Depends(get_current_user)
):
    return schedule_service.list_schedules_for_vm(str(vm_id), current_user_id)


@router.post("/", response_model=ScheduleResponse, status_code=201)
async def create_schedule(
    body: ScheduleCreate, current_user_id: str = Depends(get_current_user)
):
    return schedule_service.create_schedule(body, current_user_id)


@router.delete("/{schedule_id}")
async def delete_schedule(
    schedule_id: uuid_lib.UUID, current_user_id: str = Depends(get_current_user)
):
    schedule_service.delete_schedule(str(schedule_id), current_user_id)
    return {"detail": "Schedule deleted"}


@router.post("/{schedule_id}/toggle", response_model=ScheduleResponse)
async def toggle_schedule(
    schedule_id: uuid_lib.UUID, current_user_id: str = Depends(get_current_user)
):
    return schedule_service.toggle_schedule(str(schedule_id), current_user_id)
