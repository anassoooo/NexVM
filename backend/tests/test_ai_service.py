from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from groq import APIError

from app.models.schemas import VMResponse
from app.services import ai_service

USER_ID = "00000000-0000-0000-0000-000000000001"
VM_ID = "00000000-0000-0000-0000-000000000010"


def _vm_response(**overrides) -> VMResponse:
    now = datetime.now(timezone.utc).isoformat()
    base = {
        "id": VM_ID,
        "user_id": USER_ID,
        "name": "test-vm",
        "os": "Ubuntu 22.04",
        "ram": 1024,
        "cpu": 2,
        "disk_size": 20480,
        "vbox_id": None,
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
    return VMResponse(**base)


def _mock_groq_response(content: str, total_tokens: int = 100) -> MagicMock:
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = content
    response.usage = MagicMock()
    response.usage.total_tokens = total_tokens
    return response


@pytest.fixture(autouse=True)
def _reset_rate_limit():
    ai_service._rate_limit_store.clear()
    yield
    ai_service._rate_limit_store.clear()


@pytest.fixture(autouse=True)
def _patch_supabase():
    with patch("app.services.ai_service.get_supabase_client") as mock_get:
        mock_sb = MagicMock()
        mock_get.return_value = mock_sb
        yield mock_sb


@pytest.fixture
def _patch_list_vms():
    with patch("app.services.ai_service.vm_service.list_vms", return_value=[]) as m:
        yield m


# ── Happy paths ────────────────────────────────────────────


def test_create_vm_happy_path(_patch_supabase, _patch_list_vms):
    raw = '{"action": "create_vm", "name": "ubuntu-vm", "os": "Ubuntu 22.04", "ram": 4096}'
    created_vm = _vm_response(name="ubuntu-vm", os="Ubuntu 22.04", ram=4096)

    with (
        patch("app.services.ai_service.Groq") as mock_groq,
        patch(
            "app.services.ai_service.vm_service.create_vm", return_value=created_vm
        ) as mock_create,
    ):
        mock_groq.return_value.chat.completions.create.return_value = (
            _mock_groq_response(raw, total_tokens=150)
        )
        result = ai_service.process_ai_command("create an ubuntu vm", USER_ID)

    assert result.action == "create_vm"
    assert "ubuntu-vm" in result.result and "created" in result.result.lower()
    mock_create.assert_called_once()
    _patch_supabase.table.assert_any_call("ai_usage")
    _patch_supabase.table.assert_any_call("logs")


def test_start_vm_happy_path(_patch_supabase, _patch_list_vms):
    raw = f'{{"action": "start_vm", "vm_id": "{VM_ID}"}}'
    running_vm = _vm_response(status="running")

    with (
        patch("app.services.ai_service.Groq") as mock_groq,
        patch(
            "app.services.ai_service.vm_service.start_vm", return_value=running_vm
        ) as mock_start,
    ):
        mock_groq.return_value.chat.completions.create.return_value = (
            _mock_groq_response(raw)
        )
        result = ai_service.process_ai_command("start my vm", USER_ID)

    assert result.action == "start_vm"
    assert "Started" in result.result
    mock_start.assert_called_once_with(VM_ID, USER_ID)


def test_stop_vm_happy_path(_patch_supabase, _patch_list_vms):
    raw = f'{{"action": "stop_vm", "vm_id": "{VM_ID}"}}'
    stopped_vm = _vm_response(status="stopped")

    with (
        patch("app.services.ai_service.Groq") as mock_groq,
        patch(
            "app.services.ai_service.vm_service.stop_vm", return_value=stopped_vm
        ) as mock_stop,
    ):
        mock_groq.return_value.chat.completions.create.return_value = (
            _mock_groq_response(raw)
        )
        result = ai_service.process_ai_command("stop my vm", USER_ID)

    assert result.action == "stop_vm"
    mock_stop.assert_called_once_with(VM_ID, USER_ID)


def test_delete_vm_happy_path(_patch_supabase, _patch_list_vms):
    raw = f'{{"action": "delete_vm", "vm_id": "{VM_ID}"}}'

    with (
        patch("app.services.ai_service.Groq") as mock_groq,
        patch(
            "app.services.ai_service.vm_service.delete_vm", return_value=None
        ) as mock_delete,
    ):
        mock_groq.return_value.chat.completions.create.return_value = (
            _mock_groq_response(raw)
        )
        result = ai_service.process_ai_command("delete my vm", USER_ID)

    assert result.action == "delete_vm"
    mock_delete.assert_called_once_with(VM_ID, USER_ID)


# ── Failure paths ──────────────────────────────────────────


def test_groq_returns_non_json(_patch_supabase, _patch_list_vms):
    with patch("app.services.ai_service.Groq") as mock_groq:
        mock_groq.return_value.chat.completions.create.return_value = (
            _mock_groq_response("I cannot do that, sorry")
        )
        with pytest.raises(Exception) as exc_info:
            ai_service.process_ai_command("hello", USER_ID)

    assert exc_info.value.status_code == 400
    _patch_supabase.table.assert_any_call("ai_usage")


def test_groq_returns_unknown_action(_patch_supabase, _patch_list_vms):
    raw = f'{{"action": "reboot_vm", "vm_id": "{VM_ID}"}}'

    with patch("app.services.ai_service.Groq") as mock_groq:
        mock_groq.return_value.chat.completions.create.return_value = (
            _mock_groq_response(raw)
        )
        with pytest.raises(Exception) as exc_info:
            ai_service.process_ai_command("reboot my vm", USER_ID)

    assert exc_info.value.status_code == 400


def test_groq_returns_error_action(_patch_supabase, _patch_list_vms):
    raw = '{"action": "error", "message": "I did not understand"}'

    with patch("app.services.ai_service.Groq") as mock_groq:
        mock_groq.return_value.chat.completions.create.return_value = (
            _mock_groq_response(raw)
        )
        with pytest.raises(Exception) as exc_info:
            ai_service.process_ai_command("gibberish", USER_ID)

    assert exc_info.value.status_code == 400
    assert "I did not understand" in exc_info.value.detail


def test_groq_returns_invalid_ram(_patch_supabase, _patch_list_vms):
    raw = '{"action": "create_vm", "name": "test", "os": "Ubuntu", "ram": 99999}'

    with patch("app.services.ai_service.Groq") as mock_groq:
        mock_groq.return_value.chat.completions.create.return_value = (
            _mock_groq_response(raw)
        )
        with pytest.raises(Exception) as exc_info:
            ai_service.process_ai_command("create huge vm", USER_ID)

    assert exc_info.value.status_code == 400


def test_groq_api_error(_patch_supabase, _patch_list_vms):
    with patch("app.services.ai_service.Groq") as mock_groq:
        mock_groq.return_value.chat.completions.create.side_effect = APIError(
            message="boom",
            request=MagicMock(),
            body=None,
        )
        with pytest.raises(Exception) as exc_info:
            ai_service.process_ai_command("create vm", USER_ID)

    assert exc_info.value.status_code == 503


def test_rate_limit_exceeded(_patch_supabase, _patch_list_vms):
    raw = f'{{"action": "start_vm", "vm_id": "{VM_ID}"}}'
    running_vm = _vm_response(status="running")

    with (
        patch("app.services.ai_service.Groq") as mock_groq,
        patch("app.services.ai_service.vm_service.start_vm", return_value=running_vm),
    ):
        mock_groq.return_value.chat.completions.create.return_value = (
            _mock_groq_response(raw)
        )

        for _ in range(10):
            ai_service.process_ai_command("start", USER_ID)

        with pytest.raises(Exception) as exc_info:
            ai_service.process_ai_command("start", USER_ID)

    assert exc_info.value.status_code == 429


def test_vm_service_failure_propagates(_patch_supabase, _patch_list_vms):
    from fastapi import HTTPException

    raw = f'{{"action": "start_vm", "vm_id": "{VM_ID}"}}'

    with (
        patch("app.services.ai_service.Groq") as mock_groq,
        patch(
            "app.services.ai_service.vm_service.start_vm",
            side_effect=HTTPException(status_code=409, detail="Already running"),
        ),
    ):
        mock_groq.return_value.chat.completions.create.return_value = (
            _mock_groq_response(raw)
        )
        with pytest.raises(Exception) as exc_info:
            ai_service.process_ai_command("start it", USER_ID)

    assert exc_info.value.status_code == 409
    _patch_supabase.table.assert_any_call("ai_usage")


def test_groq_returns_invalid_vm_name(_patch_supabase, _patch_list_vms):
    raw = '{"action": "create_vm", "name": "$$bad$$", "os": "Ubuntu", "ram": 1024}'

    with patch("app.services.ai_service.Groq") as mock_groq:
        mock_groq.return_value.chat.completions.create.return_value = (
            _mock_groq_response(raw)
        )
        with pytest.raises(Exception) as exc_info:
            ai_service.process_ai_command("create bad", USER_ID)

    assert exc_info.value.status_code == 400


def test_vm_list_passed_to_system_prompt(_patch_supabase):
    raw = '{"action": "error", "message": "no action needed"}'

    with (
        patch(
            "app.services.ai_service.vm_service.list_vms",
            return_value=[_vm_response(name="my-special-vm")],
        ),
        patch("app.services.ai_service.Groq") as mock_groq,
    ):
        mock_groq.return_value.chat.completions.create.return_value = (
            _mock_groq_response(raw)
        )
        with pytest.raises(Exception):
            ai_service.process_ai_command("list", USER_ID)

        call_kwargs = mock_groq.return_value.chat.completions.create.call_args.kwargs
        system_msg = call_kwargs["messages"][0]["content"]
        assert "my-special-vm" in system_msg


def test_chat_action_happy_path(_patch_supabase, _patch_list_vms):
    raw = '{"action": "chat", "message": "Ubuntu is a popular Linux distribution known for its ease of use."}'

    with patch("app.services.ai_service.Groq") as mock_groq:
        mock_groq.return_value.chat.completions.create.return_value = (
            _mock_groq_response(raw, total_tokens=80)
        )
        result = ai_service.process_ai_command("what is Ubuntu?", USER_ID)

    assert result.action == "chat"
    assert "Ubuntu" in result.result
    _patch_supabase.table.assert_any_call("ai_usage")
    _patch_supabase.table.assert_any_call("logs")


def test_chat_action_message_too_long(_patch_supabase, _patch_list_vms):
    raw = '{"action": "chat", "message": "' + ("x" * 2001) + '"}'

    with patch("app.services.ai_service.Groq") as mock_groq:
        mock_groq.return_value.chat.completions.create.return_value = (
            _mock_groq_response(raw)
        )
        with pytest.raises(Exception) as exc_info:
            ai_service.process_ai_command("hello", USER_ID)

    assert exc_info.value.status_code == 400


def test_list_vms_returns_formatted_list(_patch_supabase):
    raw = '{"action": "list_vms"}'
    vm1 = _vm_response(name="data-science", status="running")
    vm2 = _vm_response(name="web-server", status="stopped")

    with (
        patch("app.services.ai_service.vm_service.list_vms", return_value=[vm1, vm2]),
        patch("app.services.ai_service.Groq") as mock_groq,
    ):
        mock_groq.return_value.chat.completions.create.return_value = (
            _mock_groq_response(raw)
        )
        result = ai_service.process_ai_command("list my vms", USER_ID)

    assert result.action == "list_vms"
    assert "data-science" in result.result
    assert "web-server" in result.result
    assert "running" in result.result
    assert "stopped" in result.result


def test_list_vms_empty(_patch_supabase):
    raw = '{"action": "list_vms"}'

    with (
        patch("app.services.ai_service.vm_service.list_vms", return_value=[]),
        patch("app.services.ai_service.Groq") as mock_groq,
    ):
        mock_groq.return_value.chat.completions.create.return_value = (
            _mock_groq_response(raw)
        )
        result = ai_service.process_ai_command("list my vms", USER_ID)

    assert result.action == "list_vms"
    assert "no VMs" in result.result


def test_query_analytics_uses_user_role(_patch_supabase, _patch_list_vms):
    raw = '{"action": "query_analytics", "message": "You have 2 VMs"}'

    with (
        patch("app.services.ai_service.Groq") as mock_groq,
        patch(
            "app.services.ai_service.analytics_service.get_user_analytics"
        ) as mock_user_analytics,
    ):
        mock_user_analytics.return_value = MagicMock(
            total_vms=2, running_vms=1, stopped_vms=1, error_vms=0, total_ai_commands=5
        )
        mock_profile = MagicMock()
        mock_profile.data = [{"is_admin": False}]
        _patch_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_profile
        mock_groq.return_value.chat.completions.create.return_value = (
            _mock_groq_response(raw)
        )
        result = ai_service.process_ai_command("how many VMs do I have?", USER_ID)

    assert result.action == "query_analytics"
    mock_user_analytics.assert_called_once_with(USER_ID)
