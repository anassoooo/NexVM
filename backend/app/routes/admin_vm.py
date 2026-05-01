from fastapi import APIRouter, Depends

from app.dependencies import UserClaims, get_current_admin_user
from app.models.schemas import VMActionRequest, VMResponse
from app.services import vm_service

router = APIRouter()


@router.get("/", response_model=list[VMResponse])
async def list_all_vms(_: UserClaims = Depends(get_current_admin_user)):
    return vm_service.list_all_vms()


@router.post("/start", response_model=VMResponse)
async def admin_start_vm(
    body: VMActionRequest, claims: UserClaims = Depends(get_current_admin_user)
):
    return vm_service.start_vm(str(body.vm_id), user_id=None, actor_id=claims.id)


@router.post("/stop", response_model=VMResponse)
async def admin_stop_vm(
    body: VMActionRequest, claims: UserClaims = Depends(get_current_admin_user)
):
    return vm_service.stop_vm(str(body.vm_id), user_id=None, actor_id=claims.id)


@router.post("/delete")
async def admin_delete_vm(
    body: VMActionRequest, claims: UserClaims = Depends(get_current_admin_user)
):
    vm_service.delete_vm(str(body.vm_id), user_id=None, actor_id=claims.id)
    return {"detail": "VM deleted"}


@router.post("/force-reset", response_model=VMResponse)
async def admin_force_reset_vm(
    body: VMActionRequest, claims: UserClaims = Depends(get_current_admin_user)
):
    return vm_service.force_reset_vm(str(body.vm_id), actor_id=claims.id)
