import asyncio
import inspect
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import get_db_session
from app.core.firebase import sync_user_document, verify_id_token
from app.models import User
from app.repositories.users import UserRepository

logger = structlog.get_logger(__name__)
_bearer = HTTPBearer(auto_error=False)

_USER_CACHE: dict[str, dict[str, Any]] = {}
_USER_CACHE_EXPIRY: float = 0.0
_USER_CACHE_SECONDS = 300


async def _get_jwks(_settings: Settings) -> list[dict[str, object]]:
    return []


def _test_secret(settings: Settings) -> str:
    if settings.firebase_api_key is None:
        return "test-secret"
    if hasattr(settings.firebase_api_key, "get_secret_value"):
        return settings.firebase_api_key.get_secret_value()
    return str(settings.firebase_api_key)


async def _verify_firebase_token(token: str, settings: Settings) -> dict[str, Any]:
    """Verify a Firebase ID token and return decoded claims."""
    if settings.firebase_test_mode:
        import jwt

        issuer = f"https://{settings.firebase_project_id}.firebaseapp.com/auth/v1"
        try:
            header = jwt.get_unverified_header(token)
            algorithm = str(header.get("alg", "HS256"))
            key: object = _test_secret(settings)
            if algorithm.startswith("RS"):
                kid = header.get("kid")
                jwks = await _get_jwks(settings)
                jwk = next((item for item in jwks if item.get("kid") == kid), None)
                if jwk is None:
                    raise jwt.InvalidTokenError("Unknown test key id.")
                key = jwt.algorithms.RSAAlgorithm.from_jwk(jwk)
            decoded = jwt.decode(
                token,
                key,
                algorithms=["HS256", "RS256"],
                audience=[
                    "authenticated",
                    issuer,
                ],
                issuer=issuer,
            )
        except Exception as error:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token.",
                headers={"WWW-Authenticate": "Bearer"},
            ) from error
        if decoded.get("role", "authenticated") != "authenticated":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return decoded

    try:
        return verify_id_token(token)
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from error


def _app_user_id_from_claims(decoded: dict[str, Any]) -> UUID:
    subject = decoded.get("uid") or decoded.get("sub")
    if not isinstance(subject, str) or not subject:
        raise ValueError("Authentication token is missing a user subject.")
    try:
        return UUID(subject)
    except ValueError:
        return uuid5(NAMESPACE_URL, f"firebase:{subject}")


async def _maybe_sync_firestore_user(user: User, decoded: dict[str, Any]) -> None:
    firebase_uid = decoded.get("uid") or decoded.get("sub")
    await asyncio.to_thread(
        sync_user_document,
        user_id=str(user.id),
        firebase_uid=firebase_uid if isinstance(firebase_uid, str) else None,
        email=user.email,
        display_name=user.display_name,
        preferred_financial_year=user.preferred_financial_year,
        confirmed_profile=user.confirmed_profile,
    )


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

    try:
        verified = _verify_firebase_token(credentials.credentials, settings)
        decoded = await verified if inspect.isawaitable(verified) else verified
        if isinstance(decoded, tuple):
            decoded = decoded[0]
        user_id = _app_user_id_from_claims(decoded)
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from error

    repository = UserRepository(session)
    user = await repository.get_by_id(user_id)
    if user is None:
        email = decoded.get("email")
        user = User(
            id=user_id,
            email=email if isinstance(email, str) and len(email) <= 320 else None,
        )
        user = await repository.add(user)
    elif user.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is unavailable.")
    await _maybe_sync_firestore_user(user, decoded)
    return user
