from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.services import vm_service

USER_ID = "00000000-0000-0000-0000-000000000001"
VM_ID   = "00000000-0000-0000-0000-000000000010"


def _vm_row(**overrides):
    now = datetime.now(timezone.utc).isoformat()
    base = {
        "id": VM_ID,
        "user_id": USER_ID,
        "name": "test-vm",
        "os": "ubuntu 22.04",
        "ram": 1024,
        "cpu": 2,
        "disk_size": 20480,
        "vbox_id": "vbox-uuid",
        "status": "stopped",
        "error_message": None,
        "iso_path": None,
        "vrde_enabled": False,
        "vrde_port": None,
        "nat_rules": [],
        "created_at": now,
        "updated_at": now,
    }
    base.update(overrides)
    return base


@pytest.fixture(autouse=True)
def _patch_supabase():
    with patch("app.services.vm_service.get_supabase_client") as mock_get:
        mock_sb = MagicMock()
        mock_get.return_value = mock_sb
        yield mock_sb


@pytest.fixture(autouse=True)
def _patch_vbox():
    with patch("app.services.vbox_wrapper.settings") as s:
        s.VBOXMANAGE_PATH = "VBoxManage"
        yield


_ok = MagicMock(returncode=0, stdout="", stderr="")


def _setup_vm(mock_sb, row=None):
    row = row or _vm_row()
    (mock_sb.table.return_value
     .select.return_value
     .eq.return_value
     .eq.return_value
     .execute.return_value) = MagicMock(data=[row])
    return row


def _setup_insert(mock_sb, row=None):
    row = row or _vm_row()
    (mock_sb.table.return_value
     .insert.return_value
     .execute.return_value) = MagicMock(data=[row])


def _mock_table_router(mock_sb, vm_row=None, insert_row=None, name_check_empty=True):
    vms_mock = MagicMock()
    row = vm_row or _vm_row()

    get_vm_result = MagicMock(data=[row])
    quota_result = MagicMock(data=[])
    quota_result.count = 0
    if name_check_empty:
        name_check_result = MagicMock(data=[])
    else:
        name_check_result = MagicMock(data=[{"id": "dup"}])

    execute_side_effects = [get_vm_result, quota_result, name_check_result]
    call_idx = [0]

    def _execute():
        idx = call_idx[0]
        call_idx[0] += 1
        if idx < len(execute_side_effects):
            return execute_side_effects[idx]
        return MagicMock(data=[])

    (vms_mock.select.return_value
     .eq.return_value
     .eq.return_value
     .execute).side_effect = _execute

    (vms_mock.select.return_value
     .eq.return_value
     .execute).side_effect = lambda: quota_result

    if insert_row is not None:
        (vms_mock.insert.return_value
         .execute.return_value) = MagicMock(data=[insert_row])

    def _table(name):
        if name == "vms":
            return vms_mock
        elif name == "logs":
            logs_mock = MagicMock()
            (logs_mock.insert.return_value.execute.return_value) = MagicMock(data=[])
            return logs_mock
        return MagicMock()

    mock_sb.table.side_effect = _table


# ---------------------------------------------------------------------------
# clone_vm
# ---------------------------------------------------------------------------

def test_clone_vm_ok(_patch_supabase):
    cloned_row = _vm_row(name="test-vm-copy")
    cloned_row["id"] = "00000000-0000-0000-0000-000000000020"
    _mock_table_router(_patch_supabase, insert_row=cloned_row)

    info_result = MagicMock(returncode=0, stdout='UUID="new-uuid-1234"\n', stderr="")
    clone_result = MagicMock(returncode=0, stdout="", stderr="")

    with patch("app.services.vm_service.run_vbox_command", side_effect=[clone_result, info_result]):
        result = vm_service.clone_vm(VM_ID, "test-vm-copy", USER_ID)

    assert result.name == "test-vm-copy"


def test_clone_vm_not_stopped(_patch_supabase):
    _mock_table_router(_patch_supabase, vm_row=_vm_row(status="running"))

    with pytest.raises(HTTPException) as exc:
        vm_service.clone_vm(VM_ID, "copy", USER_ID)
    assert exc.value.status_code == 409


def test_clone_vm_quota_exceeded(_patch_supabase):
    vms_mock = MagicMock()
    row = _vm_row()
    (vms_mock.select.return_value
     .eq.return_value
     .eq.return_value
     .execute.return_value) = MagicMock(data=[row])

    select_count = vms_mock.select.return_value.eq.return_value
    select_count.execute.return_value.count = 999

    def _table(name):
        if name == "vms":
            return vms_mock
        logs_mock = MagicMock()
        (logs_mock.insert.return_value.execute.return_value) = MagicMock(data=[])
        return logs_mock

    _patch_supabase.table.side_effect = _table

    with pytest.raises(HTTPException) as exc:
        vm_service.clone_vm(VM_ID, "copy", USER_ID)
    assert exc.value.status_code == 409
    assert "quota" in exc.value.detail.lower()


# ---------------------------------------------------------------------------
# export_ova
# ---------------------------------------------------------------------------

def test_export_ova_ok(_patch_supabase):
    _setup_vm(_patch_supabase)

    export_result = MagicMock(returncode=0, stdout="", stderr="")
    with patch("app.services.vm_service.run_vbox_command", return_value=export_result):
        result = vm_service.export_ova(VM_ID, "/exports/test.ova", USER_ID)

    assert "Exported to" in result["message"]


def test_export_ova_not_stopped(_patch_supabase):
    _setup_vm(_patch_supabase, _vm_row(status="running"))

    with pytest.raises(HTTPException) as exc:
        vm_service.export_ova(VM_ID, "/exports/test.ova", USER_ID)
    assert exc.value.status_code == 409


def test_export_ova_vbox_failure(_patch_supabase):
    _setup_vm(_patch_supabase)

    fail_result = MagicMock(returncode=1, stdout="", stderr="export failed")
    with patch("app.services.vm_service.run_vbox_command", return_value=fail_result):
        with pytest.raises(HTTPException) as exc:
            vm_service.export_ova(VM_ID, "/exports/test.ova", USER_ID)
    assert exc.value.status_code == 500


# ---------------------------------------------------------------------------
# import_ova
# ---------------------------------------------------------------------------

def test_import_ova_ok(_patch_supabase):
    imported_row = _vm_row(name="imported-vm", os="imported")
    imported_row["id"] = "00000000-0000-0000-0000-000000000030"

    vms_mock = MagicMock()
    quota_result = MagicMock(data=[])
    quota_result.count = 0
    (vms_mock.select.return_value
     .eq.return_value
     .execute.return_value) = quota_result

    name_check_result = MagicMock(data=[])
    (vms_mock.select.return_value
     .eq.return_value
     .eq.return_value
     .execute.return_value) = name_check_result

    (vms_mock.insert.return_value
     .execute.return_value) = MagicMock(data=[imported_row])

    def _table(name):
        if name == "vms":
            return vms_mock
        logs_mock = MagicMock()
        (logs_mock.insert.return_value.execute.return_value) = MagicMock(data=[])
        return logs_mock

    _patch_supabase.table.side_effect = _table

    import_result = MagicMock(returncode=0, stdout="", stderr="")
    info_result = MagicMock(returncode=0, stdout='UUID="import-uuid"\n', stderr="")

    with patch("app.services.vm_service.run_vbox_command", side_effect=[import_result, info_result]):
        result = vm_service.import_ova("/imports/ubuntu.ova", "imported-vm", 1024, 2, USER_ID)

    assert result.name == "imported-vm"
    assert result.os == "imported"


def test_import_ova_quota_exceeded(_patch_supabase):
    vms_mock = MagicMock()

    (vms_mock.select.return_value
     .eq.return_value
     .execute.return_value.count) = 999

    (vms_mock.select.return_value
     .eq.return_value
     .eq.return_value
     .execute.return_value) = MagicMock(data=[])

    def _table(name):
        if name == "vms":
            return vms_mock
        logs_mock = MagicMock()
        (logs_mock.insert.return_value.execute.return_value) = MagicMock(data=[])
        return logs_mock

    _patch_supabase.table.side_effect = _table

    with pytest.raises(HTTPException) as exc:
        vm_service.import_ova("/imports/ubuntu.ova", "vm", 1024, 2, USER_ID)
    assert exc.value.status_code == 409
    assert "quota" in exc.value.detail.lower()


def test_import_ova_name_conflict(_patch_supabase):
    _mock_table_router(_patch_supabase, name_check_empty=False)

    with pytest.raises(HTTPException) as exc:
        vm_service.import_ova("/imports/ubuntu.ova", "dup-name", 1024, 2, USER_ID)
    assert exc.value.status_code == 409
