import uuid as uuid_lib

from fastapi import APIRouter, Depends

from app.dependencies import get_current_user
from app.models.schemas import (
    ISOAttachRequest,
    ISODetachRequest,
    OVAExportRequest,
    OVAImportRequest,
    PortFwdAddRequest,
    PortFwdDeleteRequest,
    SnapshotActionRequest,
    SnapshotResponse,
    SnapshotTakeRequest,
    VMActionRequest,
    VMCloneRequest,
    VMCreate,
    VMModifyRequest,
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


# --- P2 routes ---

@router.post("/modify", response_model=VMResponse)
async def modify_vm(
    body: VMModifyRequest, current_user_id: str = Depends(get_current_user)
):
    return vm_service.modify_vm(str(body.vm_id), body.ram, body.cpu, current_user_id)


@router.post("/pause", response_model=VMResponse)
async def pause_vm(
    body: VMActionRequest, current_user_id: str = Depends(get_current_user)
):
    return vm_service.pause_vm(str(body.vm_id), current_user_id)


@router.post("/resume", response_model=VMResponse)
async def resume_vm(
    body: VMActionRequest, current_user_id: str = Depends(get_current_user)
):
    return vm_service.resume_vm(str(body.vm_id), current_user_id)


@router.post("/savestate", response_model=VMResponse)
async def save_state(
    body: VMActionRequest, current_user_id: str = Depends(get_current_user)
):
    return vm_service.save_state(str(body.vm_id), current_user_id)


@router.post("/portfwd", response_model=VMResponse)
async def add_port_rule(
    body: PortFwdAddRequest, current_user_id: str = Depends(get_current_user)
):
    return vm_service.add_port_rule(
        str(body.vm_id), body.name, body.protocol, body.host_port, body.guest_port, current_user_id
    )


@router.delete("/portfwd", response_model=VMResponse)
async def remove_port_rule(
    body: PortFwdDeleteRequest, current_user_id: str = Depends(get_current_user)
):
    return vm_service.remove_port_rule(str(body.vm_id), body.name, current_user_id)


@router.get("/snapshots", response_model=list[SnapshotResponse])
async def list_snapshots(
    vm_id: uuid_lib.UUID, current_user_id: str = Depends(get_current_user)
):
    return vm_service.list_snapshots(str(vm_id), current_user_id)


@router.post("/snapshot", response_model=SnapshotResponse, status_code=201)
async def take_snapshot(
    body: SnapshotTakeRequest, current_user_id: str = Depends(get_current_user)
):
    return vm_service.take_snapshot(str(body.vm_id), body.name, body.description, current_user_id)


@router.post("/snapshot/restore", response_model=VMResponse)
async def restore_snapshot(
    body: SnapshotActionRequest, current_user_id: str = Depends(get_current_user)
):
    return vm_service.restore_snapshot(str(body.vm_id), body.name, current_user_id)


@router.delete("/snapshot", status_code=204)
async def delete_snapshot(
    body: SnapshotActionRequest, current_user_id: str = Depends(get_current_user)
):
    vm_service.delete_snapshot(str(body.vm_id), body.name, current_user_id)


# --- P3 routes: Clone / Export / Import ---

@router.post("/clone", response_model=VMResponse, status_code=201)
async def clone_vm(
    body: VMCloneRequest, current_user_id: str = Depends(get_current_user)
):
    return vm_service.clone_vm(str(body.vm_id), body.new_name, current_user_id)


@router.post("/export")
async def export_ova(
    body: OVAExportRequest, current_user_id: str = Depends(get_current_user)
):
    return vm_service.export_ova(str(body.vm_id), body.output_path, current_user_id)


@router.post("/import", response_model=VMResponse, status_code=201)
async def import_ova(
    body: OVAImportRequest, current_user_id: str = Depends(get_current_user)
):
    return vm_service.import_ova(body.source_path, body.name, body.ram, body.cpu, current_user_id)
