from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ChatMessage, ChatSession, TaxComputation


class ChatRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_session(self, user_id: UUID, title: str | None) -> ChatSession:
        row = ChatSession(user_id=user_id, title=title)
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def get_session(self, session_id: UUID, user_id: UUID) -> ChatSession | None:
        statement = select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.user_id == user_id,
            ChatSession.deleted_at.is_(None),
        )
        return (await self.session.execute(statement)).scalar_one_or_none()

    async def list_sessions(self, user_id: UUID) -> list[ChatSession]:
        statement = (
            select(ChatSession)
            .where(ChatSession.user_id == user_id, ChatSession.deleted_at.is_(None))
            .order_by(ChatSession.updated_at.desc(), ChatSession.id.desc())
        )
        return list((await self.session.execute(statement)).scalars().all())

    async def list_messages(self, session_id: UUID, *, limit: int = 100) -> list[ChatMessage]:
        statement = (
            select(ChatMessage)
            .where(
                ChatMessage.chat_session_id == session_id,
                ChatMessage.deleted_at.is_(None),
            )
            .order_by(ChatMessage.created_at, ChatMessage.id)
            .limit(limit)
        )
        return list((await self.session.execute(statement)).scalars().all())

    async def add_message(
        self,
        session_id: UUID,
        role: str,
        content: str,
        citations: list[dict[str, str]] | None = None,
    ) -> ChatMessage:
        row = ChatMessage(
            chat_session_id=session_id,
            role=role,
            content=content,
            citations=citations or [],
            created_at=datetime.now(UTC),
        )
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def latest_computation(self, user_id: UUID) -> TaxComputation | None:
        statement = (
            select(TaxComputation)
            .where(
                TaxComputation.user_id == user_id,
                TaxComputation.deleted_at.is_(None),
                TaxComputation.computation_type.in_(("old", "new", "compare")),
            )
            .order_by(TaxComputation.created_at.desc(), TaxComputation.id.desc())
            .limit(1)
        )
        return (await self.session.execute(statement)).scalar_one_or_none()
