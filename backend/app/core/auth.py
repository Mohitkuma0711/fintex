import asyncio
import time
from typing import Any
from uuid import UUID

import httpx
import jwt
import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import get_db_session
from app.models import User
from app.repositories.users import UserRepository

logger = structlog.get_logger(__name__)
_bearer = HTTPBearer(auto_error=False)
_jwks_lock = asyncio.Lock()
_jwks_keys: list[dict[str, Any]] = []
_jwks_expiry = 0.0
_JWKS_CACHE_SECONDS = 300


def _test_secret(settings: Settings) -> str:
    if settings.supabase_jwt_secret is not None:
        return settings.supabase_jwt_secret.get_secret_value()
    return "super-secret-jwt-token-with-at-least-32-chars-long"


async def _get_jwks(settings: Settings) -> list[dict[str, Any]]:
    global _jwks_expiry, _jwks_keys
    if _jwks_keys and time.monotonic() < _jwks_expiry:
        return _jwks_keys
    if not settings.supabase_url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is not configured.",
        )
    async with _jwks_lock:
        if _jwks_keys and time.monotonic() < _jwks_expiry:
            return _jwks_keys
        url = f"{settings.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(url)
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError) as error:
            logger.warning("supabase_jwks_unavailable", error_type=type(error).__name__)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication verification is temporarily unavailable.",
            ) from error
        keys = payload.get("keys") if isinstance(payload, dict) else None
        if not isinstance(keys, list):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication verification is temporarily unavailable.",
            )
        _jwks_keys = [key for key in keys if isinstance(key, dict)]
        _jwks_expiry = time.monotonic() + _JWKS_CACHE_SECONDS
        return _jwks_keys


async def _verification_key(token: str, settings: Settings) -> tuple[Any, list[str]]:
    is_dev_env = settings.supabase_test_mode or settings.app_env.lower() in {
        "development",
        "dev",
        "test",
        "local",
    }
    try:
        header = jwt.get_unverified_header(token)
        algorithm = header.get("alg")
        if algorithm == "HS256":
            if settings.supabase_jwt_secret is not None:
                return settings.supabase_jwt_secret.get_secret_value(), ["HS256"]
            if is_dev_env:
                return _test_secret(settings), ["HS256"]
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication is not configured.",
            )
        if algorithm not in {"ES256", "RS256"}:
            raise jwt.InvalidAlgorithmError(f"Unsupported signing algorithm: {algorithm}")
        kid = header.get("kid")
        if not isinstance(kid, str):
            raise jwt.InvalidTokenError("Missing signing key identifier")
        keys = await _get_jwks(settings)
        matching = [
            key for key in keys if key.get("kid") == kid and key.get("alg") in (None, algorithm)
        ]
        if not matching:
            global _jwks_expiry
            _jwks_expiry = 0
            keys = await _get_jwks(settings)
            matching = [
                key for key in keys if key.get("kid") == kid and key.get("alg") in (None, algorithm)
            ]
        if len(matching) != 1:
            raise jwt.InvalidTokenError("Unknown signing key")
        return jwt.PyJWK.from_dict(matching[0]).key, [algorithm]
    except HTTPException:
        raise
    except (jwt.PyJWTError, KeyError, TypeError, ValueError) as error:
        logger.warning(
            "supabase_verification_key_failed",
            error_type=type(error).__name__,
            error=str(error),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from error


async def _verify_supabase_token(token: str, settings: Settings) -> dict[str, Any]:
    key, algorithms = await _verification_key(token, settings)
    is_dev_env = settings.supabase_test_mode or settings.app_env.lower() in {
        "development",
        "dev",
        "test",
        "local",
    }
    issuer = f"{settings.supabase_url.rstrip('/')}/auth/v1" if settings.supabase_url else None
    decode_kwargs: dict[str, Any] = {
        "algorithms": algorithms,
        "audience": "authenticated",
        "options": {"require": ["exp", "sub"]},
    }
    if issuer and not is_dev_env:
        decode_kwargs["issuer"] = issuer

    try:
        claims = jwt.decode(token, key, **decode_kwargs)
        if claims.get("role") != "authenticated":
            raise jwt.InvalidTokenError("Token is not for an authenticated user")
        return claims
    except (jwt.PyJWTError, KeyError, TypeError, ValueError) as error:
        logger.warning(
            "supabase_token_decode_failed",
            error_type=type(error).__name__,
            error=str(error),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from error


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    settings: Settings = Depends(get_settings),
    session: AsyncSession = Depends(get_db_session),
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    claims = await _verify_supabase_token(credentials.credentials, settings)
    try:
        auth_user_id = UUID(claims["sub"])
    except (ValueError, KeyError, TypeError) as error:
        logger.warning("invalid_supabase_user_id_in_claims", error=str(error))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from error

    repository = UserRepository(session)
    user = await repository.get_by_id(auth_user_id)
    if user is None:
        email = claims.get("email")
        user = User(
            id=auth_user_id,
            email=email if isinstance(email, str) and len(email) <= 320 else None,
        )
        user = await repository.add(user)
    elif user.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is unavailable.")
    return user
