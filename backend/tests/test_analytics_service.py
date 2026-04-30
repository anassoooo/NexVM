from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.services import analytics_service

USER_ID = "00000000-0000-0000-0000-000000000001"
ADMIN_ID = "00000000-0000-0000-0000-000000000002"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sb_result(rows: list) -> MagicMock:
    m = MagicMock()
    m.data = rows
    return m


def _make_supabase(
    vms: list | None = None,
    ai_rows: list | None = None,
    profile_rows: list | None = None,
) -> MagicMock:
    sb = MagicMock()
    # Chain: table().select().eq().execute() or table().select().execute()
    sb.table.return_value.select.return_value.eq.return_value.execute.return_value = (
        _sb_result([])
    )
    sb.table.return_value.select.return_value.execute.return_value = _sb_result([])

    def _table(name: str):
        t = MagicMock()

        def _select(cols):
            s = MagicMock()

            def _eq(col, val):
                e = MagicMock()
                if name == "vms" and vms is not None:
                    e.execute.return_value = _sb_result(vms)
                elif name == "ai_usage" and ai_rows is not None:
                    e.execute.return_value = _sb_result(ai_rows)
                else:
                    e.execute.return_value = _sb_result([])
                return e

            s.eq = _eq

            # no-eq execute (admin queries)
            if name == "profiles" and profile_rows is not None:
                s.execute.return_value = _sb_result(profile_rows)
            elif name == "vms" and vms is not None:
                s.execute.return_value = _sb_result(vms)
            elif name == "ai_usage" and ai_rows is not None:
                s.execute.return_value = _sb_result(ai_rows)
            else:
                s.execute.return_value = _sb_result([])

            return s

        t.select = _select
        return t

    sb.table.side_effect = _table
    return sb


# ---------------------------------------------------------------------------
# Unit tests: get_user_analytics
# ---------------------------------------------------------------------------

@patch("app.services.analytics_service.get_supabase_client")
def test_user_analytics_vm_counts(mock_get):
    """Returns correct VM status counts for a user."""
    vms = [
        {"status": "running"},
        {"status": "stopped"},
        {"status": "stopped"},
        {"status": "error"},
    ]
    mock_get.return_value = _make_supabase(vms=vms, ai_rows=[])

    result = analytics_service.get_user_analytics(USER_ID)

    assert result.total_vms == 4
    assert result.running_vms == 1
    assert result.stopped_vms == 2
    assert result.error_vms == 1


@patch("app.services.analytics_service.get_supabase_client")
def test_user_analytics_ai_command_count(mock_get):
    """Returns correct AI command count for a user."""
    ai_rows = [{"id": "a"}, {"id": "b"}, {"id": "c"}]
    mock_get.return_value = _make_supabase(vms=[], ai_rows=ai_rows)

    result = analytics_service.get_user_analytics(USER_ID)

    assert result.total_ai_commands == 3


@patch("app.services.analytics_service.get_supabase_client")
def test_user_analytics_all_zeros(mock_get):
    """Returns all zeros when user has no VMs or AI usage."""
    mock_get.return_value = _make_supabase(vms=[], ai_rows=[])

    result = analytics_service.get_user_analytics(USER_ID)

    assert result.total_vms == 0
    assert result.running_vms == 0
    assert result.stopped_vms == 0
    assert result.error_vms == 0
    assert result.total_ai_commands == 0


# ---------------------------------------------------------------------------
# Unit tests: get_admin_analytics
# ---------------------------------------------------------------------------

@patch("app.services.analytics_service.get_supabase_client")
def test_admin_analytics_total_users(mock_get):
    """Returns correct total_users from profiles table."""
    profiles = [{"id": "u1"}, {"id": "u2"}]
    mock_get.return_value = _make_supabase(
        vms=[], ai_rows=[], profile_rows=profiles
    )

    result = analytics_service.get_admin_analytics()

    assert result.total_users == 2


@patch("app.services.analytics_service.get_supabase_client")
def test_admin_analytics_vm_counts(mock_get):
    """Returns correct VM counts across all users."""
    vms = [
        {"status": "running"},
        {"status": "running"},
        {"status": "stopped"},
        {"status": "error"},
    ]
    mock_get.return_value = _make_supabase(
        vms=vms, ai_rows=[], profile_rows=[]
    )

    result = analytics_service.get_admin_analytics()

    assert result.total_vms == 4
    assert result.running_vms == 2
    assert result.stopped_vms == 1
    assert result.error_vms == 1


@patch("app.services.analytics_service.get_supabase_client")
def test_admin_analytics_ai_commands(mock_get):
    """Returns correct total AI command count across all users."""
    ai_rows = [{"id": "x"}, {"id": "y"}]
    mock_get.return_value = _make_supabase(
        vms=[], ai_rows=ai_rows, profile_rows=[]
    )

    result = analytics_service.get_admin_analytics()

    assert result.total_ai_commands == 2


# ---------------------------------------------------------------------------
# Integration tests (TestClient via dependency_overrides)
# ---------------------------------------------------------------------------

client = TestClient(app)


@patch("app.services.analytics_service.get_supabase_client")
def test_admin_endpoint_rejects_non_admin(mock_get):
    """Non-admin user gets 403 from /analytics/admin."""
    from fastapi import HTTPException
    from app.dependencies import get_current_admin_user, get_current_user

    mock_get.return_value = _make_supabase(vms=[], ai_rows=[], profile_rows=[])

    def raise_admin_error():
        raise HTTPException(status_code=403, detail="Admin access required")

    app.dependency_overrides[get_current_user] = lambda: USER_ID
    app.dependency_overrides[get_current_admin_user] = raise_admin_error
    try:
        resp = client.get("/api/v1/analytics/admin")
        assert resp.status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_analytics_no_token_rejected():
    """Request without token is rejected (401 from JWT decode)."""
    resp = client.get("/api/v1/analytics")
    assert resp.status_code == 401
