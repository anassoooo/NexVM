import uuid as uuid_lib

from fastapi import APIRouter, Depends

from app.dependencies import UserClaims, get_current_user
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
    VMMetrics,
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
async def list_vms(claims: UserClaims = Depends(get_current_user)):
    return vm_service.list_vms(claims.id)


@router.post("/status", response_model=VMResponse)
async def get_vm_status(
    body: VMActionRequest, claims: UserClaims = Depends(get_current_user)
):
    return vm_service.get_vm_status(str(body.vm_id), claims.id)


@router.post("/sync", response_model=VMResponse)
async def sync_vm_status(
    body: VMActionRequest, claims: UserClaims = Depends(get_current_user)
):
    return vm_service.sync_vm_status(str(body.vm_id), claims.id)


@router.post("/create", response_model=VMResponse, status_code=201)
async def create_vm(body: VMCreate, claims: UserClaims = Depends(get_current_user)):
    return vm_service.create_vm(body, claims.id)


@router.post("/start", response_model=VMResponse)
async def start_vm(
    body: VMActionRequest, claims: UserClaims = Depends(get_current_user)
):
    return vm_service.start_vm(str(body.vm_id), claims.id)


@router.post("/stop", response_model=VMResponse)
async def stop_vm(
    body: VMActionRequest, claims: UserClaims = Depends(get_current_user)
):
    return vm_service.stop_vm(str(body.vm_id), claims.id)


@router.post("/delete")
async def delete_vm(
    body: VMActionRequest, claims: UserClaims = Depends(get_current_user)
):
    vm_service.delete_vm(str(body.vm_id), claims.id)
    return {"detail": "VM deleted"}


@router.post("/iso", response_model=VMResponse)
async def attach_iso(
    body: ISOAttachRequest, claims: UserClaims = Depends(get_current_user)
):
    return vm_service.attach_iso(str(body.vm_id), body.iso_path, claims.id)


@router.delete("/iso", response_model=VMResponse)
async def detach_iso(
    body: ISODetachRequest, claims: UserClaims = Depends(get_current_user)
):
    return vm_service.detach_iso(str(body.vm_id), claims.id)


@router.post("/vrde", response_model=VMResponse)
async def enable_vrde(
    body: VRDEEnableRequest, claims: UserClaims = Depends(get_current_user)
):
    return vm_service.enable_vrde(str(body.vm_id), body.port, claims.id)


@router.delete("/vrde", response_model=VMResponse)
async def disable_vrde(
    body: VRDEDisableRequest, claims: UserClaims = Depends(get_current_user)
):
    return vm_service.disable_vrde(str(body.vm_id), claims.id)


# --- P2 routes ---

@router.post("/modify", response_model=VMResponse)
async def modify_vm(
    body: VMModifyRequest, claims: UserClaims = Depends(get_current_user)
):
    return vm_service.modify_vm(str(body.vm_id), body.ram, body.cpu, claims.id)


@router.post("/pause", response_model=VMResponse)
async def pause_vm(
    body: VMActionRequest, claims: UserClaims = Depends(get_current_user)
):
    return vm_service.pause_vm(str(body.vm_id), claims.id)


@router.post("/resume", response_model=VMResponse)
async def resume_vm(
    body: VMActionRequest, claims: UserClaims = Depends(get_current_user)
):
    return vm_service.resume_vm(str(body.vm_id), claims.id)


@router.post("/savestate", response_model=VMResponse)
async def save_state(
    body: VMActionRequest, claims: UserClaims = Depends(get_current_user)
):
    return vm_service.save_state(str(body.vm_id), claims.id)


@router.post("/portfwd", response_model=VMResponse)
async def add_port_rule(
    body: PortFwdAddRequest, claims: UserClaims = Depends(get_current_user)
):
    return vm_service.add_port_rule(
        str(body.vm_id), body.name, body.protocol, body.host_port, body.guest_port, claims.id
    )


@router.delete("/portfwd", response_model=VMResponse)
async def remove_port_rule(
    body: PortFwdDeleteRequest, claims: UserClaims = Depends(get_current_user)
):
    return vm_service.remove_port_rule(str(body.vm_id), body.name, claims.id)


@router.get("/snapshots", response_model=list[SnapshotResponse])
async def list_snapshots(
    vm_id: uuid_lib.UUID, claims: UserClaims = Depends(get_current_user)
):
    return vm_service.list_snapshots(str(vm_id), claims.id)


@router.post("/snapshot", response_model=SnapshotResponse, status_code=201)
async def take_snapshot(
    body: SnapshotTakeRequest, claims: UserClaims = Depends(get_current_user)
):
    return vm_service.take_snapshot(str(body.vm_id), body.name, body.description, claims.id)


@router.post("/snapshot/restore", response_model=VMResponse)
async def restore_snapshot(
    body: SnapshotActionRequest, claims: UserClaims = Depends(get_current_user)
):
    return vm_service.restore_snapshot(str(body.vm_id), body.name, claims.id)


@router.delete("/snapshot", status_code=204)
async def delete_snapshot(
    body: SnapshotActionRequest, claims: UserClaims = Depends(get_current_user)
):
    vm_service.delete_snapshot(str(body.vm_id), body.name, claims.id)


# --- Metrics ---

@router.get("/metrics", response_model=VMMetrics)
async def get_vm_metrics(
    vm_id: uuid_lib.UUID, claims: UserClaims = Depends(get_current_user)
):
    return vm_service.get_vm_metrics(str(vm_id), claims.id)


# --- P3 routes: Clone / Export / Import ---

@router.post("/clone", response_model=VMResponse, status_code=201)
async def clone_vm(
    body: VMCloneRequest, claims: UserClaims = Depends(get_current_user)
):
    return vm_service.clone_vm(str(body.vm_id), body.new_name, claims.id)


@router.post("/export")
async def export_ova(
    body: OVAExportRequest, claims: UserClaims = Depends(get_current_user)
):
    return vm_service.export_ova(str(body.vm_id), body.output_path, claims.id)


@router.post("/import", response_model=VMResponse, status_code=201)
async def import_ova(
    body: OVAImportRequest, claims: UserClaims = Depends(get_current_user)
):
    return vm_service.import_ova(body.source_path, body.name, body.ram, body.cpu, claims.id)
