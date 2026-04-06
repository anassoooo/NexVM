import subprocess
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.models.schemas import VMCreate
from app.services import vm_service

USER_ID = "00000000-0000-0000-0000-000000000001"
VM_ID = "00000000-0000-0000-0000-000000000010"
OTHER_USER_ID = "00000000-0000-0000-0000-000000000002"


def _vm_row(**overrides):
    now = datetime.now(timezone.utc).isoformat()
    base = {
        "id": VM_ID,
        "user_id": USER_ID,
        "name": "test-vm",
        "os": "Ubuntu 22.04",
        "ram": 1024,
        "status": "stopped",
        "error_message": None,
        "created_at": now,
        "updated_at": now,
    }
    base.update(overrides)
    return base


def _mock_supabase():
    mock = MagicMock()
    chain = mock.table.return_value.select.return_value.eq.return_value.eq.return_value
    chain.execute.return_value = MagicMock(data=[_vm_row()])
    return mock


@pytest.fixture(autouse=True)
def _patch_supabase():
    with patch("app.services.vm_service.get_supabase_client") as mock_get:
        mock_sb = MagicMock()
        mock_get.return_value = mock_sb
        yield mock_sb


@pytest.fixture(autouse=True)
def _patch_vbox_path():
    with patch("app.services.vbox_wrapper.settings") as mock_settings:
        mock_settings.VBOXMANAGE_PATH = "VBoxManage"
        yield


def _setup_select_vm(mock_sb, row=None):
    if row is None:
        row = _vm_row()
    mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[row]
    )
    return row


# ── create_vm ──────────────────────────────────────────────


def test_create_vm_success(_patch_supabase):
    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.stderr = ""

    _patch_supabase.table.return_value.insert.return_value.execute.return_value = (
        MagicMock(data=[_vm_row()])
    )

    with patch("app.services.vm_service.run_vbox_command", return_value=mock_proc):
        result = vm_service.create_vm(
            VMCreate(name="test-vm", os="Ubuntu 22.04", ram=1024), USER_ID
        )

    assert result.name == "test-vm"
    assert result.status == "stopped"
    _patch_supabase.table.assert_any_call("logs")


def test_create_vm_name_conflict_409(_patch_supabase):
    mock_proc = MagicMock()
    mock_proc.returncode = 1
    mock_proc.stderr = "VirtualBox error: Machine settings file already exists"

    with patch("app.services.vm_service.run_vbox_command", return_value=mock_proc):
        with pytest.raises(Exception) as exc_info:
            vm_service.create_vm(VMCreate(name="dup", os="Ubuntu", ram=512), USER_ID)
        assert exc_info.value.status_code == 409


def test_create_vm_generic_failure_500(_patch_supabase):
    mock_proc = MagicMock()
    mock_proc.returncode = 1
    mock_proc.stderr = "some internal error"

    with patch("app.services.vm_service.run_vbox_command", return_value=mock_proc):
        with pytest.raises(Exception) as exc_info:
            vm_service.create_vm(
                VMCreate(name="fail-vm", os="Ubuntu", ram=512), USER_ID
            )
        assert exc_info.value.status_code == 500
    _patch_supabase.table.assert_any_call("logs")


# ── start_vm ───────────────────────────────────────────────


def test_start_vm_stopped_to_running(_patch_supabase):
    _setup_select_vm(_patch_supabase, _vm_row(status="stopped"))
    mock_proc = MagicMock(returncode=0, stderr="")
    running_row = _vm_row(status="running")
    _patch_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[running_row]
    )

    with patch("app.services.vm_service.run_vbox_command", return_value=mock_proc):
        result = vm_service.start_vm(VM_ID, USER_ID)

    assert result.status == "running"


def test_start_vm_error_retry_to_running(_patch_supabase):
    _setup_select_vm(
        _patch_supabase, _vm_row(status="error", error_message="old error")
    )
    mock_proc = MagicMock(returncode=0, stderr="")
    running_row = _vm_row(status="running")
    _patch_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[running_row]
    )

    with patch("app.services.vm_service.run_vbox_command", return_value=mock_proc):
        result = vm_service.start_vm(VM_ID, USER_ID)

    assert result.status == "running"


def test_start_vm_running_409(_patch_supabase):
    _setup_select_vm(_patch_supabase, _vm_row(status="running"))

    with patch("app.services.vm_service.run_vbox_command"):
        with pytest.raises(Exception) as exc_info:
            vm_service.start_vm(VM_ID, USER_ID)
        assert exc_info.value.status_code == 409


def test_start_vm_starting_409(_patch_supabase):
    _setup_select_vm(_patch_supabase, _vm_row(status="starting"))

    with patch("app.services.vm_service.run_vbox_command"):
        with pytest.raises(Exception) as exc_info:
            vm_service.start_vm(VM_ID, USER_ID)
        assert exc_info.value.status_code == 409


def test_start_vm_vbox_failure_sets_error(_patch_supabase):
    _setup_select_vm(_patch_supabase, _vm_row(status="stopped"))
    mock_proc = MagicMock(returncode=1, stderr="panic")

    with patch("app.services.vm_service.run_vbox_command", return_value=mock_proc):
        with pytest.raises(Exception) as exc_info:
            vm_service.start_vm(VM_ID, USER_ID)
        assert exc_info.value.status_code == 500

    _patch_supabase.table.assert_any_call("logs")


def test_start_vm_timeout_sets_error(_patch_supabase):
    _setup_select_vm(_patch_supabase, _vm_row(status="stopped"))

    with patch(
        "app.services.vm_service.run_vbox_command",
        side_effect=subprocess.TimeoutExpired(cmd="VBoxManage", timeout=30),
    ):
        with pytest.raises(Exception) as exc_info:
            vm_service.start_vm(VM_ID, USER_ID)
        assert exc_info.value.status_code == 500

    _patch_supabase.table.assert_any_call("logs")


# ── stop_vm ────────────────────────────────────────────────


def test_stop_vm_running_to_stopped(_patch_supabase):
    _setup_select_vm(_patch_supabase, _vm_row(status="running"))
    mock_proc = MagicMock(returncode=0, stderr="")
    stopped_row = _vm_row(status="stopped")
    _patch_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[stopped_row]
    )

    with patch("app.services.vm_service.run_vbox_command", return_value=mock_proc):
        result = vm_service.stop_vm(VM_ID, USER_ID)

    assert result.status == "stopped"


def test_stop_vm_stopped_409(_patch_supabase):
    _setup_select_vm(_patch_supabase, _vm_row(status="stopped"))

    with patch("app.services.vm_service.run_vbox_command"):
        with pytest.raises(Exception) as exc_info:
            vm_service.stop_vm(VM_ID, USER_ID)
        assert exc_info.value.status_code == 409


def test_stop_vm_vbox_failure_sets_error(_patch_supabase):
    _setup_select_vm(_patch_supabase, _vm_row(status="running"))
    mock_proc = MagicMock(returncode=1, stderr="halt error")

    with patch("app.services.vm_service.run_vbox_command", return_value=mock_proc):
        with pytest.raises(Exception) as exc_info:
            vm_service.stop_vm(VM_ID, USER_ID)
        assert exc_info.value.status_code == 500

    _patch_supabase.table.assert_any_call("logs")


# ── delete_vm ──────────────────────────────────────────────


def test_delete_vm_stopped_success(_patch_supabase):
    _setup_select_vm(_patch_supabase, _vm_row(status="stopped"))
    mock_proc = MagicMock(returncode=0, stderr="")

    with patch("app.services.vm_service.run_vbox_command", return_value=mock_proc):
        vm_service.delete_vm(VM_ID, USER_ID)

    _patch_supabase.table.assert_any_call("logs")


def test_delete_vm_running_409(_patch_supabase):
    _setup_select_vm(_patch_supabase, _vm_row(status="running"))

    with patch("app.services.vm_service.run_vbox_command"):
        with pytest.raises(Exception) as exc_info:
            vm_service.delete_vm(VM_ID, USER_ID)
        assert exc_info.value.status_code == 409


def test_delete_vm_vbox_failure_preserves_db(_patch_supabase):
    _setup_select_vm(_patch_supabase, _vm_row(status="stopped"))
    mock_proc = MagicMock(returncode=1, stderr="cannot delete")

    with patch("app.services.vm_service.run_vbox_command", return_value=mock_proc):
        with pytest.raises(Exception) as exc_info:
            vm_service.delete_vm(VM_ID, USER_ID)
        assert exc_info.value.status_code == 500

    delete_calls = [
        c
        for c in _patch_supabase.table.return_value.delete.return_value.eq.return_value.execute.call_args_list
    ]
    assert len(delete_calls) == 0
    _patch_supabase.table.assert_any_call("logs")


# ── get_vm_or_404 ──────────────────────────────────────────


def test_get_vm_found(_patch_supabase):
    _setup_select_vm(_patch_supabase)
    result = vm_service.get_vm_status(VM_ID, USER_ID)
    assert result.name == "test-vm"


def test_get_vm_wrong_user_404(_patch_supabase):
    chain = _patch_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value
    chain.execute.return_value = MagicMock(data=[])

    with pytest.raises(Exception) as exc_info:
        vm_service.get_vm_status(VM_ID, OTHER_USER_ID)
    assert exc_info.value.status_code == 404


def test_get_vm_not_found(_patch_supabase):
    chain = _patch_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value
    chain.execute.return_value = MagicMock(data=[])

    with pytest.raises(Exception) as exc_info:
        vm_service.get_vm_status("00000000-0000-0000-0000-999999999999", USER_ID)
    assert exc_info.value.status_code == 404
