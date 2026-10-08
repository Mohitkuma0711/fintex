from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Document, ExtractionResult


class DocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_user(self, user_id: UUID) -> list[Document]:
        result = await self.session.execute(
            select(Document)
            .where(Document.user_id == user_id, Document.deleted_at.is_(None))
            .order_by(Document.created_at.desc())
        )
        return list(result.scalars())

    async def add(self, document: Document) -> Document:
        self.session.add(document)
        await self.session.commit()
        await self.session.refresh(document)
        return document

    async def update(self, document: Document, **changes: object) -> Document:
        for key, value in changes.items():
            setattr(document, key, value)
        await self.session.commit()
        await self.session.refresh(document)
        return document

    async def add_extraction(self, extraction: ExtractionResult) -> ExtractionResult:
        self.session.add(extraction)
        await self.session.commit()
        await self.session.refresh(extraction)
        return extraction

    async def get_for_user(self, document_id: UUID, user_id: UUID) -> Document | None:
        result = await self.session.execute(
            select(Document).where(
                Document.id == document_id,
                Document.user_id == user_id,
                Document.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, document_id: UUID) -> Document | None:
        result = await self.session.execute(
            select(Document).where(Document.id == document_id, Document.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def get_extraction_for_document(self, document_id: UUID) -> ExtractionResult | None:
        result = await self.session.execute(
            select(ExtractionResult)
            .where(
                ExtractionResult.document_id == document_id,
                ExtractionResult.deleted_at.is_(None),
            )
            .order_by(ExtractionResult.created_at.desc())
        )
        return result.scalars().first()

    async def get_extraction_for_user(
        self, extraction_id: UUID, user_id: UUID
    ) -> tuple[ExtractionResult, Document] | None:
        result = await self.session.execute(
            select(ExtractionResult, Document)
            .join(Document, Document.id == ExtractionResult.document_id)
            .where(
                ExtractionResult.id == extraction_id,
                ExtractionResult.deleted_at.is_(None),
                Document.user_id == user_id,
                Document.deleted_at.is_(None),
            )
        )
        return result.one_or_none()

    async def soft_delete(self, document: Document) -> None:
        document.deleted_at = datetime.now(UTC)
        await self.session.commit()
