from fastapi import APIRouter, Depends

from app.dependencies import get_current_user
from app.models.schemas import VMActionRequest, VMCreate, VMResponse
from app.services import vm_service

router = APIRouter()


@router.get("/", response_model=list[VMResponse])
async def list_vms(current_user_id: str = Depends(get_current_user)):
    return vm_service.list_vms(current_user_id)


@router.post("/status", response_model=VMResponse)
async def get_vm_status(
    body: VMActionRequest, current_user_id: str = Depends(get_current_user)
):
    return vm_service.get_vm_status(body.vm_id, current_user_id)


@router.post("/create", response_model=VMResponse, status_code=201)
async def create_vm(body: VMCreate, current_user_id: str = Depends(get_current_user)):
    return vm_service.create_vm(body, current_user_id)


@router.post("/start", response_model=VMResponse)
async def start_vm(
    body: VMActionRequest, current_user_id: str = Depends(get_current_user)
):
    return vm_service.start_vm(body.vm_id, current_user_id)


@router.post("/stop", response_model=VMResponse)
async def stop_vm(
    body: VMActionRequest, current_user_id: str = Depends(get_current_user)
):
    return vm_service.stop_vm(body.vm_id, current_user_id)


@router.post("/delete")
async def delete_vm(
    body: VMActionRequest, current_user_id: str = Depends(get_current_user)
):
    vm_service.delete_vm(body.vm_id, current_user_id)
    return {"detail": "VM deleted"}
