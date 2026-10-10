import httpx
import structlog
from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models import (
    ChatMessage,
    ChatSession,
    Document,
    ExtractionResult,
    Suggestion,
    TaxComputation,
    User,
)

logger = structlog.get_logger(__name__)


async def _delete_supabase_identity(user_id: str, settings: Settings) -> None:
    if not settings.supabase_url or not settings.supabase_service_role_key:
        return
    url = f"{settings.supabase_url.rstrip('/')}/auth/v1/admin/users/{user_id}"
    key = settings.supabase_service_role_key.get_secret_value()
    headers = {"apikey": key, "Authorization": f"Bearer {key}"}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.delete(url, headers=headers)
            if response.status_code not in (200, 404):
                response.raise_for_status()
    except Exception as error:
        logger.warning("supabase_identity_delete_failed", error_type=type(error).__name__)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Your data cleanup could not be completed. Please retry or contact support.",
        ) from error


class PrivacyService:
    def __init__(
        self,
        session: AsyncSession,
        settings: Settings,
        storage: any = None,
    ) -> None:
        self.session = session
        self.settings = settings
        self.storage = storage

    async def _delete_supabase_identity(self, user_id: str) -> None:
        await _delete_supabase_identity(user_id, self.settings)

    async def delete_user_data(self, user: User) -> None:
        chat_session_ids = select(ChatSession.id).where(ChatSession.user_id == user.id)
        document_ids = select(Document.id).where(Document.user_id == user.id)
        documents = list(
            (await self.session.execute(select(Document).where(Document.user_id == user.id)))
            .scalars()
            .all()
        )
        if self.storage is not None:
            for document in documents:
                await self.storage.delete(document.storage_path)
        await self._delete_supabase_identity(str(user.id))

        await self.session.execute(
            delete(ChatMessage).where(ChatMessage.chat_session_id.in_(chat_session_ids))
        )
        await self.session.execute(delete(ChatSession).where(ChatSession.user_id == user.id))
        await self.session.execute(
            delete(ExtractionResult).where(ExtractionResult.document_id.in_(document_ids))
        )
        await self.session.execute(delete(Suggestion).where(Suggestion.user_id == user.id))
        await self.session.execute(delete(Document).where(Document.user_id == user.id))
        await self.session.execute(delete(TaxComputation).where(TaxComputation.user_id == user.id))
        await self.session.delete(user)
        await self.session.commit()
