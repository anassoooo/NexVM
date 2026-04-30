from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.services import vm_service

USER_ID = "00000000-0000-0000-0000-000000000001"
VM_ID   = "00000000-0000-0000-0000-000000000010"
VM_ID2  = "00000000-0000-0000-0000-000000000011"

ISO_PATH = "/isos/ubuntu-22.04.iso"


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
def _patch_vbox_path():
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


# ---------------------------------------------------------------------------
# attach_iso
# ---------------------------------------------------------------------------

def test_attach_iso_ok(tmp_path, _patch_supabase):
    iso = tmp_path / "ubuntu.iso"
    iso.write_bytes(b"")
    mock_sb = _patch_supabase
    _setup_vm(mock_sb)
    _setup_update(mock_sb, _vm_row(iso_path=str(iso)))

    ok = MagicMock(returncode=0, stdout="", stderr="")
    with patch("app.services.vm_service.run_vbox_command", return_value=ok):
        result = vm_service.attach_iso(VM_ID, str(iso), USER_ID)

    assert result.iso_path == str(iso)


def test_attach_iso_vm_not_stopped(_patch_supabase):
    mock_sb = _patch_supabase
    _setup_vm(mock_sb, _vm_row(status="running"))

    with pytest.raises(HTTPException) as exc:
        vm_service.attach_iso(VM_ID, ISO_PATH, USER_ID)
    assert exc.value.status_code == 409


def test_attach_iso_file_not_found(_patch_supabase):
    mock_sb = _patch_supabase
    _setup_vm(mock_sb)

    with pytest.raises(HTTPException) as exc:
        vm_service.attach_iso(VM_ID, "/nonexistent/ubuntu.iso", USER_ID)
    assert exc.value.status_code == 422


# ---------------------------------------------------------------------------
# detach_iso
# ---------------------------------------------------------------------------

def test_detach_iso_ok(tmp_path, _patch_supabase):
    mock_sb = _patch_supabase
    _setup_vm(mock_sb, _vm_row(iso_path=ISO_PATH))
    _setup_update(mock_sb, _vm_row(iso_path=None))

    ok = MagicMock(returncode=0, stdout="", stderr="")
    with patch("app.services.vm_service.run_vbox_command", return_value=ok):
        result = vm_service.detach_iso(VM_ID, USER_ID)

    assert result.iso_path is None


def test_detach_iso_no_iso(_patch_supabase):
    mock_sb = _patch_supabase
    _setup_vm(mock_sb, _vm_row(iso_path=None))

    with pytest.raises(HTTPException) as exc:
        vm_service.detach_iso(VM_ID, USER_ID)
    assert exc.value.status_code == 409


def test_detach_iso_vm_not_stopped(_patch_supabase):
    mock_sb = _patch_supabase
    _setup_vm(mock_sb, _vm_row(status="running", iso_path=ISO_PATH))

    with pytest.raises(HTTPException) as exc:
        vm_service.detach_iso(VM_ID, USER_ID)
    assert exc.value.status_code == 409


# ---------------------------------------------------------------------------
# enable_vrde
# ---------------------------------------------------------------------------

def test_enable_vrde_ok(_patch_supabase):
    mock_sb = _patch_supabase
    _setup_vm(mock_sb)
    # no port conflict
    (mock_sb.table.return_value
     .select.return_value
     .eq.return_value
     .neq.return_value
     .execute.return_value) = MagicMock(data=[])
    _setup_update(mock_sb, _vm_row(vrde_enabled=True, vrde_port=3389))

    ok = MagicMock(returncode=0, stdout="", stderr="")
    with patch("app.services.vm_service.run_vbox_command", return_value=ok):
        result = vm_service.enable_vrde(VM_ID, 3389, USER_ID)

    assert result.vrde_enabled is True
    assert result.vrde_port == 3389


def test_enable_vrde_vm_not_stopped(_patch_supabase):
    mock_sb = _patch_supabase
    _setup_vm(mock_sb, _vm_row(status="running"))

    with pytest.raises(HTTPException) as exc:
        vm_service.enable_vrde(VM_ID, 3389, USER_ID)
    assert exc.value.status_code == 409


def test_enable_vrde_port_conflict(_patch_supabase):
    mock_sb = _patch_supabase
    _setup_vm(mock_sb)
    # port already used by another VM
    (mock_sb.table.return_value
     .select.return_value
     .eq.return_value
     .neq.return_value
     .execute.return_value) = MagicMock(data=[{"id": VM_ID2}])

    with pytest.raises(HTTPException) as exc:
        vm_service.enable_vrde(VM_ID, 3389, USER_ID)
    assert exc.value.status_code == 409
    assert "already in use" in exc.value.detail


# ---------------------------------------------------------------------------
# disable_vrde
# ---------------------------------------------------------------------------

def test_disable_vrde_ok(_patch_supabase):
    mock_sb = _patch_supabase
    _setup_vm(mock_sb, _vm_row(vrde_enabled=True, vrde_port=3389))
    _setup_update(mock_sb, _vm_row(vrde_enabled=False, vrde_port=None))

    ok = MagicMock(returncode=0, stdout="", stderr="")
    with patch("app.services.vm_service.run_vbox_command", return_value=ok):
        result = vm_service.disable_vrde(VM_ID, USER_ID)

    assert result.vrde_enabled is False
    assert result.vrde_port is None


def test_disable_vrde_already_off(_patch_supabase):
    mock_sb = _patch_supabase
    _setup_vm(mock_sb, _vm_row(vrde_enabled=False))

    with pytest.raises(HTTPException) as exc:
        vm_service.disable_vrde(VM_ID, USER_ID)
    assert exc.value.status_code == 409
