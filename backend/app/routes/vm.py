from fastapi import APIRouter, Depends

from app.dependencies import get_current_user
from app.models.schemas import (
    ISOAttachRequest,
    ISODetachRequest,
    VMActionRequest,
    VMCreate,
    VMResponse,
    VRDEDisableRequest,
    VRDEEnableRequest,
)
from app.services import vm_service

router = APIRouter()


@router.get("/public", response_model=list[VMResponse])
async def list_all_vms_public():
    return vm_service.list_all_vms()


@router.get("/", response_model=list[VMResponse])
async def list_vms(current_user_id: str = Depends(get_current_user)):
    return vm_service.list_vms(current_user_id)


@router.post("/status", response_model=VMResponse)
async def get_vm_status(
    body: VMActionRequest, current_user_id: str = Depends(get_current_user)
):
    return vm_service.get_vm_status(str(body.vm_id), current_user_id)


@router.post("/sync", response_model=VMResponse)
async def sync_vm_status(
    body: VMActionRequest, current_user_id: str = Depends(get_current_user)
):
    """Sync VM status from VirtualBox actual state."""
    return vm_service.sync_vm_status(str(body.vm_id), current_user_id)


@router.post("/create", response_model=VMResponse, status_code=201)
async def create_vm(body: VMCreate, current_user_id: str = Depends(get_current_user)):
    return vm_service.create_vm(body, current_user_id)


@router.post("/start", response_model=VMResponse)
async def start_vm(
    body: VMActionRequest, current_user_id: str = Depends(get_current_user)
):
    return vm_service.start_vm(str(body.vm_id), current_user_id)


@router.post("/stop", response_model=VMResponse)
async def stop_vm(
    body: VMActionRequest, current_user_id: str = Depends(get_current_user)
):
    return vm_service.stop_vm(str(body.vm_id), current_user_id)


@router.post("/delete")
async def delete_vm(
    body: VMActionRequest, current_user_id: str = Depends(get_current_user)
):
    vm_service.delete_vm(str(body.vm_id), current_user_id)
    return {"detail": "VM deleted"}


@router.post("/iso", response_model=VMResponse)
async def attach_iso(
    body: ISOAttachRequest, current_user_id: str = Depends(get_current_user)
):
    return vm_service.attach_iso(str(body.vm_id), body.iso_path, current_user_id)


@router.delete("/iso", response_model=VMResponse)
async def detach_iso(
    body: ISODetachRequest, current_user_id: str = Depends(get_current_user)
):
    return vm_service.detach_iso(str(body.vm_id), current_user_id)


@router.post("/vrde", response_model=VMResponse)
async def enable_vrde(
    body: VRDEEnableRequest, current_user_id: str = Depends(get_current_user)
):
    return vm_service.enable_vrde(str(body.vm_id), body.port, current_user_id)


@router.delete("/vrde", response_model=VMResponse)
async def disable_vrde(
    body: VRDEDisableRequest, current_user_id: str = Depends(get_current_user)
):
    return vm_service.disable_vrde(str(body.vm_id), current_user_id)
