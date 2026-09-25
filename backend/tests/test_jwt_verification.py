"""Authentication checks that do not need a live Supabase project."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from jose import jwt
from jose.exceptions import JWTError

from app.config import settings
from app.dependencies import _decode_jwt


def _legacy_token(secret: str) -> str:
    return jwt.encode(
        {
            "sub": "test-user",
            "aud": "authenticated",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        secret,
        algorithm="HS256",
    )


def test_legacy_token_requires_explicit_secret() -> None:
    secret = "local-test-secret"
    token = _legacy_token(secret)

    with patch.object(settings, "SUPABASE_JWT_SECRET", None):
        with pytest.raises(JWTError, match="not configured"):
            _decode_jwt(token)

    with patch.object(settings, "SUPABASE_JWT_SECRET", secret):
        assert _decode_jwt(token)["sub"] == "test-user"


def test_asymmetric_token_uses_matching_public_key() -> None:
    public_key = {"kid": "current", "alg": "ES256", "kty": "EC"}
    with (
        patch("app.dependencies.jwt.get_unverified_header", return_value={"alg": "ES256", "kid": "current"}),
        patch("app.dependencies._get_jwks_keys", return_value=[public_key]),
        patch("app.dependencies.jwt.decode", return_value={"sub": "test-user"}) as decode,
    ):
        assert _decode_jwt("header.payload.signature")["sub"] == "test-user"
    decode.assert_called_once_with(
        "header.payload.signature", public_key, algorithms=["ES256"], audience="authenticated"
    )


def test_unsupported_algorithm_is_rejected() -> None:
    with patch("app.dependencies.jwt.get_unverified_header", return_value={"alg": "none"}):
        with pytest.raises(JWTError, match="Unsupported"):
            _decode_jwt("header.payload.signature")
