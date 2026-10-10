from uuid import uuid4
from datetime import UTC, datetime, timedelta
import pytest
import jwt
from fastapi import HTTPException
from app.core.auth import _verify_supabase_token
from app.core.config import Settings

TEST_SECRET = "super-secret-jwt-token-with-at-least-32-chars-long"


@pytest.mark.asyncio
async def test_verify_dev_token_in_development_env():
    settings = Settings(
        app_env="development",
        supabase_url="https://demo.supabase.co",
        supabase_jwt_secret=TEST_SECRET,
        supabase_test_mode=False,
    )
    user_id = str(uuid4())
    token = jwt.encode(
        {
            "sub": user_id,
            "role": "authenticated",
            "aud": "authenticated",
            "exp": datetime.now(UTC) + timedelta(hours=1),
        },
        TEST_SECRET,
        algorithm="HS256",
    )

    claims = await _verify_supabase_token(token, settings)
    assert claims["sub"] == user_id
    assert claims["role"] == "authenticated"


@pytest.mark.asyncio
async def test_reject_token_with_invalid_role():
    settings = Settings(
        app_env="development",
        supabase_url="https://demo.supabase.co",
        supabase_jwt_secret=TEST_SECRET,
        supabase_test_mode=False,
    )
    user_id = str(uuid4())
    token = jwt.encode(
        {
            "sub": user_id,
            "role": "anon",
            "aud": "authenticated",
            "exp": datetime.now(UTC) + timedelta(hours=1),
        },
        TEST_SECRET,
        algorithm="HS256",
    )

    with pytest.raises(HTTPException) as exc_info:
        await _verify_supabase_token(token, settings)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_reject_expired_token():
    settings = Settings(
        app_env="development",
        supabase_url="https://demo.supabase.co",
        supabase_jwt_secret=TEST_SECRET,
        supabase_test_mode=False,
    )
    user_id = str(uuid4())
    token = jwt.encode(
        {
            "sub": user_id,
            "role": "authenticated",
            "aud": "authenticated",
            "exp": datetime.now(UTC) - timedelta(hours=1),
        },
        TEST_SECRET,
        algorithm="HS256",
    )

    with pytest.raises(HTTPException) as exc_info:
        await _verify_supabase_token(token, settings)
    assert exc_info.value.status_code == 401
