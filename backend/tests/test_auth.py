from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi import APIRouter, Depends, FastAPI
from httpx import ASGITransport, AsyncClient
from jose import jwt

from app.config import settings
from app.dependencies import get_current_user

TEST_USER_ID = "00000000-0000-0000-0000-000000000001"


@pytest.fixture(autouse=True)
def legacy_test_secret(monkeypatch):
    monkeypatch.setattr(settings, "SUPABASE_JWT_SECRET", "local-test-secret")


def _make_token(
    user_id: str = TEST_USER_ID,
    exp_offset: int = 3600,
    aud: str = "authenticated",
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "aud": aud,
        "exp": now + timedelta(seconds=exp_offset),
        "iat": now,
        "iss": settings.SUPABASE_URL,
        "role": "authenticated",
    }
    return jwt.encode(payload, settings.SUPABASE_JWT_SECRET, algorithm="HS256")


@pytest.fixture
def valid_token():
    return _make_token()


@pytest.fixture
def expired_token():
    return _make_token(exp_offset=-10)


@pytest.fixture
def mock_supabase():
    mock = MagicMock()
    mock.table.return_value.select.return_value.eq.return_value.execute.return_value = (
        MagicMock(data=[{"id": TEST_USER_ID}])
    )
    return mock


@pytest.fixture
def test_app():
    app = FastAPI()
    router = APIRouter()

    @router.get("/protected")
    async def protected(user_id: str = Depends(get_current_user)):
        return {"user_id": user_id}

    app.include_router(router, prefix="/api/v1")
    return app


@pytest.mark.asyncio
async def test_valid_jwt_returns_200(valid_token, test_app, mock_supabase):
    with patch("app.dependencies.get_supabase_client", return_value=mock_supabase):
        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/protected",
                headers={"Authorization": f"Bearer {valid_token}"},
            )
            assert response.status_code == 200
            assert response.json()["user_id"]["id"] == TEST_USER_ID


@pytest.mark.asyncio
async def test_expired_jwt_returns_401(expired_token, test_app):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/protected",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_missing_authorization_returns_401(test_app):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/protected")
        assert response.status_code == 401
