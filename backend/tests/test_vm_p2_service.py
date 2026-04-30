from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.services import vm_service

USER_ID = "00000000-0000-0000-0000-000000000001"
VM_ID   = "00000000-0000-0000-0000-000000000010"
SNAP_ID = "00000000-0000-0000-0000-000000000020"


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


def _snap_row(**overrides):
    now = datetime.now(timezone.utc).isoformat()
    base = {
        "id": SNAP_ID,
        "vm_id": VM_ID,
        "name": "snap1",
        "description": None,
        "created_at": now,
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


def _setup_vm(mock_sb, row=None):
    row = row or _vm_row()
    (mock_sb.table.return_value
     .select.return_value
     .eq.return_value
     .eq.return_value
     .execute.return_value) = MagicMock(data=[row])
    return row


def _setup_update(mock_sb, row=None):
    row = row or _vm_row()
    (mock_sb.table.return_value
     .update.return_value
     .eq.return_value
     .execute.return_value) = MagicMock(data=[row])


_ok = MagicMock(returncode=0, stdout="", stderr="")


# ---------------------------------------------------------------------------
# modify_vm
# ---------------------------------------------------------------------------

def test_modify_vm_ok(_patch_supabase):
    mock_sb = _patch_supabase
    _setup_vm(mock_sb)
    _setup_update(mock_sb, _vm_row(ram=4096, cpu=4))

    with patch("app.services.vm_service.run_vbox_command", return_value=_ok):
        result = vm_service.modify_vm(VM_ID, 4096, 4, USER_ID)

    assert result.ram == 4096
    assert result.cpu == 4


def test_modify_vm_not_stopped(_patch_supabase):
    _setup_vm(_patch_supabase, _vm_row(status="running"))
    with pytest.raises(HTTPException) as exc:
        vm_service.modify_vm(VM_ID, 2048, None, USER_ID)
    assert exc.value.status_code == 409


def test_modify_vm_no_fields():
    with pytest.raises(ValueError):
        from app.models.schemas import VMModifyRequest
        VMModifyRequest(vm_id=VM_ID)


# ---------------------------------------------------------------------------
# pause_vm / resume_vm
# ---------------------------------------------------------------------------

def test_pause_vm_ok(_patch_supabase):
    mock_sb = _patch_supabase
    _setup_vm(mock_sb, _vm_row(status="running"))
    _setup_update(mock_sb, _vm_row(status="paused"))

    with patch("app.services.vm_service.run_vbox_command", return_value=_ok):
        result = vm_service.pause_vm(VM_ID, USER_ID)

    assert result.status.value == "paused"


def test_pause_vm_not_running(_patch_supabase):
    _setup_vm(_patch_supabase, _vm_row(status="stopped"))
    with pytest.raises(HTTPException) as exc:
        vm_service.pause_vm(VM_ID, USER_ID)
    assert exc.value.status_code == 409


def test_resume_vm_ok(_patch_supabase):
    mock_sb = _patch_supabase
    _setup_vm(mock_sb, _vm_row(status="paused"))
    _setup_update(mock_sb, _vm_row(status="running"))

    with patch("app.services.vm_service.run_vbox_command", return_value=_ok):
        result = vm_service.resume_vm(VM_ID, USER_ID)

    assert result.status.value == "running"


def test_resume_vm_not_paused(_patch_supabase):
    _setup_vm(_patch_supabase, _vm_row(status="running"))
    with pytest.raises(HTTPException) as exc:
        vm_service.resume_vm(VM_ID, USER_ID)
    assert exc.value.status_code == 409


# ---------------------------------------------------------------------------
# save_state
# ---------------------------------------------------------------------------

def test_save_state_ok(_patch_supabase):
    mock_sb = _patch_supabase
    _setup_vm(mock_sb, _vm_row(status="running"))
    _setup_update(mock_sb, _vm_row(status="stopped"))

    with patch("app.services.vm_service.run_vbox_command", return_value=_ok):
        result = vm_service.save_state(VM_ID, USER_ID)

    assert result.status.value == "stopped"


def test_save_state_not_running(_patch_supabase):
    _setup_vm(_patch_supabase, _vm_row(status="stopped"))
    with pytest.raises(HTTPException) as exc:
        vm_service.save_state(VM_ID, USER_ID)
    assert exc.value.status_code == 409


# ---------------------------------------------------------------------------
# add_port_rule / remove_port_rule
# ---------------------------------------------------------------------------

def test_add_port_rule_ok(_patch_supabase):
    mock_sb = _patch_supabase
    _setup_vm(mock_sb, _vm_row(nat_rules=[]))
    expected_rules = [{"name": "http", "protocol": "tcp", "host_port": 8080, "guest_port": 80}]
    _setup_update(mock_sb, _vm_row(nat_rules=expected_rules))

    with patch("app.services.vm_service.run_vbox_command", return_value=_ok):
        result = vm_service.add_port_rule(VM_ID, "http", "tcp", 8080, 80, USER_ID)

    assert len(result.nat_rules) == 1
    assert result.nat_rules[0].name == "http"


def test_add_port_rule_duplicate(_patch_supabase):
    existing = [{"name": "http", "protocol": "tcp", "host_port": 8080, "guest_port": 80}]
    _setup_vm(_patch_supabase, _vm_row(nat_rules=existing))

    with pytest.raises(HTTPException) as exc:
        vm_service.add_port_rule(VM_ID, "http", "tcp", 9090, 90, USER_ID)
    assert exc.value.status_code == 409


def test_remove_port_rule_ok(_patch_supabase):
    mock_sb = _patch_supabase
    existing = [{"name": "http", "protocol": "tcp", "host_port": 8080, "guest_port": 80}]
    _setup_vm(mock_sb, _vm_row(nat_rules=existing))
    _setup_update(mock_sb, _vm_row(nat_rules=[]))

    with patch("app.services.vm_service.run_vbox_command", return_value=_ok):
        result = vm_service.remove_port_rule(VM_ID, "http", USER_ID)

    assert result.nat_rules == []


def test_remove_port_rule_not_found(_patch_supabase):
    _setup_vm(_patch_supabase, _vm_row(nat_rules=[]))
    with pytest.raises(HTTPException) as exc:
        vm_service.remove_port_rule(VM_ID, "nonexistent", USER_ID)
    assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# snapshots
# ---------------------------------------------------------------------------

def _mock_table_router(mock_sb, vm_row=None, snap_rows=None, snap_insert=None):
    """Route mock_sb.table() calls to per-table mocks."""
    vms_mock   = MagicMock()
    snaps_mock = MagicMock()

    row = vm_row or _vm_row()
    (vms_mock.select.return_value
     .eq.return_value
     .eq.return_value
     .execute.return_value) = MagicMock(data=[row])

    (snaps_mock.select.return_value
     .eq.return_value
     .eq.return_value
     .execute.return_value) = MagicMock(data=snap_rows if snap_rows is not None else [])

    if snap_insert is not None:
        (snaps_mock.insert.return_value
         .execute.return_value) = MagicMock(data=[snap_insert])

    (snaps_mock.delete.return_value
     .eq.return_value
     .eq.return_value
     .execute.return_value) = MagicMock(data=[])

    def _table(name):
        return vms_mock if name == "vms" else snaps_mock

    mock_sb.table.side_effect = _table


def test_take_snapshot_ok(_patch_supabase):
    _mock_table_router(_patch_supabase, snap_rows=[], snap_insert=_snap_row())

    with patch("app.services.vm_service.run_vbox_command", return_value=_ok):
        result = vm_service.take_snapshot(VM_ID, "snap1", "", USER_ID)

    assert result.name == "snap1"


def test_restore_snapshot_ok(_patch_supabase):
    _mock_table_router(_patch_supabase, snap_rows=[_snap_row()])

    with patch("app.services.vm_service.run_vbox_command", return_value=_ok):
        result = vm_service.restore_snapshot(VM_ID, "snap1", USER_ID)

    assert str(result.id) == VM_ID


def test_delete_snapshot_ok(_patch_supabase):
    _mock_table_router(_patch_supabase, snap_rows=[_snap_row()])

    with patch("app.services.vm_service.run_vbox_command", return_value=_ok):
        vm_service.delete_snapshot(VM_ID, "snap1", USER_ID)
