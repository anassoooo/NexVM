"""Spec 012 F1 — VMs are addressed by vbox_id and registered under host-unique names."""

import re
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.models.schemas import VMCreate
from app.services import vm_service
from tests.test_vm_service import USER_ID, VM_ID, _setup_quota_check, _setup_select_vm, _vm_row

VBOX_UUID = "12345678-1234-1234-1234-123456789012"


@pytest.fixture(autouse=True)
def _patch_supabase():
    with patch("app.services.vm_service.get_supabase_client") as mock_get:
        mock_sb = MagicMock()
        mock_get.return_value = mock_sb
        mock_sb.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[_vm_row()])
        yield mock_sb


def _ok(stdout: str = "") -> MagicMock:
    return MagicMock(returncode=0, stderr="", stdout=stdout)


def _create(mock_sb, name: str = "ubuntu") -> list[list[str]]:
    _setup_quota_check(mock_sb, count=0)
    created = _ok(f"Virtual machine is created and registered. UUID: {VBOX_UUID}")
    with patch("app.services.vm_service.run_vbox_command", return_value=created) as run:
        vm_service.create_vm(VMCreate(name=name, os="Ubuntu", ram=1024), USER_ID)
    return [c.args[0] for c in run.call_args_list]


def _createvm_name(calls: list[list[str]]) -> str:
    cmd = next(c for c in calls if c[1] == "createvm")
    return cmd[cmd.index("--name") + 1]


def test_create_registers_host_unique_name(_patch_supabase):
    calls = _create(_patch_supabase)
    assert re.fullmatch(r"ubuntu-[0-9a-f]{8}", _createvm_name(calls))


def test_same_display_name_gets_different_vbox_names(_patch_supabase):
    first = _createvm_name(_create(_patch_supabase))
    second = _createvm_name(_create(_patch_supabase))
    assert first != second


def test_create_configures_vm_by_uuid(_patch_supabase):
    calls = _create(_patch_supabase)
    for cmd in calls:
        if cmd[1] in ("modifyvm", "storagectl", "storageattach"):
            assert cmd[2] == VBOX_UUID


def test_already_exists_returns_409_without_deleting_anything(_patch_supabase):
    _setup_quota_check(_patch_supabase, count=0)
    exists = MagicMock(returncode=1, stdout="", stderr="Machine settings file already exists")
    with (
        patch("app.services.vm_service.run_vbox_command", return_value=exists) as run,
        patch("shutil.rmtree") as rmtree,
    ):
        with pytest.raises(HTTPException) as exc_info:
            vm_service.create_vm(VMCreate(name="ubuntu", os="Ubuntu", ram=1024), USER_ID)

    assert exc_info.value.status_code == 409
    assert [c.args[0][1] for c in run.call_args_list] == ["createvm"]
    rmtree.assert_not_called()


@pytest.mark.parametrize(
    ("action", "status"),
    [("start_vm", "stopped"), ("stop_vm", "running"), ("delete_vm", "stopped")],
)
def test_lifecycle_actions_use_vbox_id(_patch_supabase, action, status):
    _setup_select_vm(_patch_supabase, _vm_row(status=status, vbox_id=VBOX_UUID))
    _patch_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[_vm_row(status=status, vbox_id=VBOX_UUID)]
    )
    with patch("app.services.vm_service.run_vbox_command", return_value=_ok('VMState="poweroff"')) as run:
        getattr(vm_service, action)(VM_ID, USER_ID)

    vm_args = [c.args[0][2] for c in run.call_args_list]
    assert vm_args and all(arg == VBOX_UUID for arg in vm_args)


def test_vbox_ref_never_falls_back_to_display_name():
    assert vm_service._vbox_ref({"name": "x", "vbox_id": VBOX_UUID}) == VBOX_UUID
    with pytest.raises(HTTPException) as exc_info:
        vm_service._vbox_ref({"name": "ubuntu", "vbox_id": None})
    assert exc_info.value.status_code == 409


def test_create_without_parsable_uuid_removes_the_new_vm(_patch_supabase):
    _setup_quota_check(_patch_supabase, count=0)
    with patch("app.services.vm_service.run_vbox_command", return_value=_ok("no uuid here")) as run:
        with pytest.raises(HTTPException) as exc_info:
            vm_service.create_vm(VMCreate(name="ubuntu", os="Ubuntu", ram=1024), USER_ID)

    assert exc_info.value.status_code == 500
    calls = [c.args[0] for c in run.call_args_list]
    created_as = _createvm_name(calls)
    assert calls[-1][1:] == ["unregistervm", created_as, "--delete"]
    _patch_supabase.table.return_value.insert.assert_not_called()
