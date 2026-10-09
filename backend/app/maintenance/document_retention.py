import asyncio
from datetime import UTC, datetime

import structlog
from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import SessionFactory
from app.models import Document
from app.repositories.documents import DocumentRepository
from app.services.storage.firebase_storage import FirebaseStorage

logger = structlog.get_logger(__name__)


async def delete_expired_documents() -> int:
    settings = get_settings()
    storage = FirebaseStorage(settings)
    deleted_count = 0
    async with SessionFactory() as session:
        expired = list(
            (
                await session.execute(
                    select(Document).where(
                        Document.deleted_at.is_(None),
                        Document.auto_delete_at.is_not(None),
                        Document.auto_delete_at <= datetime.now(UTC),
                    )
                )
            )
            .scalars()
            .all()
        )
        repository = DocumentRepository(session)
        for document in expired:
            await storage.delete(document.storage_path)
            extraction = await repository.get_extraction_for_document(document.id)
            if extraction is not None:
                extraction.deleted_at = datetime.now(UTC)
                await session.commit()
            await repository.soft_delete(document)
            deleted_count += 1
    logger.info("document_retention_completed", deleted_count=deleted_count)
    return deleted_count


def main() -> None:
    print(f"Deleted {asyncio.run(delete_expired_documents())} expired document(s).")


if __name__ == "__main__":
    main()
