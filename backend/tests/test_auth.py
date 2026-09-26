import base64
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import APIRouter, Depends, FastAPI
from httpx import ASGITransport, AsyncClient
from jose import jwt

from app.config import settings
from app.dependencies import get_current_user

TEST_USER_ID = "00000000-0000-0000-0000-000000000001"


@pytest.fixture(autouse=True)
def signing_key(monkeypatch):
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_numbers = private_key.public_key().public_numbers()

    def encode_coordinate(value: int) -> str:
        return base64.urlsafe_b64encode(value.to_bytes(32, "big")).rstrip(b"=").decode()

    public_jwk = {
        "kty": "EC",
        "crv": "P-256",
        "x": encode_coordinate(public_numbers.x),
        "y": encode_coordinate(public_numbers.y),
        "kid": "test-key",
        "alg": "ES256",
    }
    monkeypatch.setattr("app.dependencies._get_jwks_keys", lambda: [public_jwk])
    return private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )


def _make_token(
    signing_key: bytes,
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
    return jwt.encode(payload, signing_key, algorithm="ES256", headers={"kid": "test-key"})


@pytest.fixture
def valid_token(signing_key):
    return _make_token(signing_key)


@pytest.fixture
def expired_token(signing_key):
    return _make_token(signing_key, exp_offset=-10)


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
