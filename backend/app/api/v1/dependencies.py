from collections.abc import AsyncIterator, Callable

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.config import Settings, get_settings
from app.core.database import SessionFactory, get_db_session
from app.models import User
from app.services.chat.service import ChatService
from app.services.documents import DocumentService
from app.services.extraction.jobs import ExtractionJob
from app.services.extraction.orchestrator import ExtractionOrchestrator
from app.services.extraction.virus_scan import PlaceholderVirusScanner, VirusScanner
from app.services.storage.supabase_storage import SupabaseStorage
from app.services.suggestions.service import SuggestionService
from app.services.tax import TaxService
from app.services.tax_engine.rules import RulesetVersion
from app.services.users import UserService
from app.services.validation.service import ExtractionValidationService


def get_storage(settings: Settings = Depends(get_settings)) -> SupabaseStorage:
    return SupabaseStorage(settings)


def get_virus_scanner() -> VirusScanner:
    return PlaceholderVirusScanner()


async def get_extraction_job(
    settings: Settings = Depends(get_settings),
    storage: SupabaseStorage = Depends(get_storage),
    scanner: VirusScanner = Depends(get_virus_scanner),
) -> ExtractionJob:
    return ExtractionJob(
        SessionFactory,
        storage,
        ExtractionOrchestrator(settings, storage),
        scanner,
    )


async def get_document_service(
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
    storage: SupabaseStorage = Depends(get_storage),
) -> AsyncIterator[DocumentService]:
    yield DocumentService(session, settings, storage)


async def get_extraction_validation_service(
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
    storage: SupabaseStorage = Depends(get_storage),
) -> AsyncIterator[ExtractionValidationService]:
    yield ExtractionValidationService(session, settings, storage)


async def get_tax_service(
    session: AsyncSession = Depends(get_db_session),
) -> AsyncIterator[TaxService]:
    yield TaxService(session)


async def get_suggestion_service(
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> AsyncIterator[SuggestionService]:
    yield SuggestionService(session, settings)


async def get_chat_service(
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
    user: User = Depends(get_current_user),
) -> AsyncIterator[ChatService]:
    yield ChatService(session, settings, user)


async def get_user_service(
    session: AsyncSession = Depends(get_db_session),
) -> AsyncIterator[UserService]:
    yield UserService(session)


def require_configured_rules(
    settings: Settings = Depends(get_settings),
) -> Callable[[str], RulesetVersion]:
    from app.services.tax_engine.rules import RULES_FILE, RuleConfigurationError, load_rules

    def select(financial_year: str) -> RulesetVersion:
        try:
            rules = load_rules(financial_year, path=settings.tax_rules_file or RULES_FILE)
            rules.require_ready()
            return rules
        except RuleConfigurationError as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Verified tax rules are not available for the requested financial year.",
            ) from error

    return select
