from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.v1.dependencies import get_extraction_validation_service
from app.core.auth import get_current_user
from app.models import User
from app.schemas.validation import (
    ConfirmExtractionRequest,
    ConfirmExtractionResponse,
    ExtractionValidationResponse,
)
from app.services.validation.service import ExtractionValidationService

router = APIRouter()


@router.get(
    "/extractions/{extraction_id}/validation",
    response_model=ExtractionValidationResponse,
    summary="Validate extracted document values before taxpayer confirmation",
)
async def get_extraction_validation(
    extraction_id: UUID,
    user: User = Depends(get_current_user),
    service: ExtractionValidationService = Depends(get_extraction_validation_service),
) -> ExtractionValidationResponse:
    return await service.get_validation(user, extraction_id)


@router.put(
    "/extractions/{extraction_id}/confirm",
    response_model=ConfirmExtractionResponse,
    summary="Save corrected extraction values and confirm taxpayer profile",
)
async def confirm_extraction(
    extraction_id: UUID,
    request: ConfirmExtractionRequest,
    user: User = Depends(get_current_user),
    service: ExtractionValidationService = Depends(get_extraction_validation_service),
) -> ConfirmExtractionResponse:
    return await service.confirm(user, extraction_id, request)
