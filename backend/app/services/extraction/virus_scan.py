from typing import Protocol
from uuid import UUID

import structlog

logger = structlog.get_logger(__name__)


class VirusScanner(Protocol):
    async def scan(self, document_id: UUID, content: bytes) -> str: ...


class PlaceholderVirusScanner:
    async def scan(self, document_id: UUID, _content: bytes) -> str:
        logger.warning("virus_scan_not_configured", document_id=str(document_id))
        return "not_scanned"


async def scan_document(
    scanner: VirusScanner,
    document_id: UUID,
    content: bytes,
) -> str:
    return await scanner.scan(document_id, content)
