"""Spec 012 F8 — names passed to VBoxManage can't be read as options or split rule strings."""

import uuid

import pytest
from pydantic import ValidationError

from app.models.schemas import (
    PortFwdAddRequest,
    PortFwdDeleteRequest,
    SnapshotActionRequest,
    SnapshotTakeRequest,
)

VM_ID = uuid.uuid4()
BUILDERS = {
    "snapshot-take": lambda n: SnapshotTakeRequest(vm_id=VM_ID, name=n),
    "snapshot-action": lambda n: SnapshotActionRequest(vm_id=VM_ID, name=n),
    "portfwd-add": lambda n: PortFwdAddRequest(vm_id=VM_ID, name=n, protocol="tcp", host_port=8080, guest_port=80),
    "portfwd-delete": lambda n: PortFwdDeleteRequest(vm_id=VM_ID, name=n),
}


@pytest.mark.parametrize("build", BUILDERS.values(), ids=BUILDERS.keys())
@pytest.mark.parametrize("name", ["snap 1", "v1.2_final", "http"])
def test_valid_names_accepted(build, name):
    assert build(name).name == name


@pytest.mark.parametrize("build", BUILDERS.values(), ids=BUILDERS.keys())
@pytest.mark.parametrize("name", ["--delete", "-x", "a,tcp,,22,,22", " lead", "x" * 51, "snap\n"])
def test_unsafe_names_rejected(build, name):
    with pytest.raises(ValidationError):
        build(name)
