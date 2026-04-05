import time
from datetime import datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from jose import jwt

from app.config import settings

TEST_USER_ID = "00000000-0000-0000-0000-000000000001"


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


@pytest.mark.asyncio
async def test_valid_jwt_returns_200(valid_token):
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/health",
            headers={"Authorization": f"Bearer {valid_token}"},
        )
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_expired_jwt_returns_401(expired_token):
    from app.main import app
    from app.dependencies import get_current_user
    from fastapi import Depends, APIRouter

    test_router = APIRouter()

    @test_router.get("/test-protected")
    async def protected(user_id: str = Depends(get_current_user)):
        return {"user_id": user_id}

    app.include_router(test_router, prefix="/api/v1")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/test-protected",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_missing_authorization_returns_401():
    from app.main import app
    from app.dependencies import get_current_user
    from fastapi import Depends, APIRouter

    test_router = APIRouter()

    @test_router.get("/test-protected-no-auth")
    async def protected(user_id: str = Depends(get_current_user)):
        return {"user_id": user_id}

    app.include_router(test_router, prefix="/api/v1")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/test-protected-no-auth")
        assert response.status_code == 401
