from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.pii import mask_pan, mask_pans_in_text
from app.models import Document, ExtractionResult, User
from app.repositories.documents import DocumentRepository
from app.repositories.users import UserRepository
from app.schemas.extraction import Form16Extraction, SalarySlipExtraction
from app.schemas.validation import (
    ConfirmExtractionRequest,
    ConfirmExtractionResponse,
    ExtractionValidationResponse,
)
from app.services.storage.firebase_storage import FirebaseStorage
from app.services.tax_engine.rules import (
    RULES_FILE,
    RuleConfigurationError,
    is_official_source,
    load_rules,
)
from app.services.validation.checks import (
    financial_year_for_assessment_year,
    validation_issues,
)


class ExtractionValidationService:
    def __init__(
        self,
        session: AsyncSession,
        settings: Settings,
        storage: FirebaseStorage,
    ) -> None:
        self.session = session
        self.settings = settings
        self.storage = storage
        self.repository = DocumentRepository(session)

    async def get_validation(self, user: User, extraction_id: UUID) -> ExtractionValidationResponse:
        extraction_row, document = await self._get_record(user, extraction_id)
        extraction = self._parse_extraction(extraction_row, document)
        issues = validation_issues(
            extraction,
            confidence_threshold=self.settings.validation_low_confidence_threshold,
            section_80c_cap=self._verified_80c_cap(extraction),
        )
        preview_url = await self.storage.create_signed_url(document.storage_path)
        response_extraction = self._masked_extraction(extraction)
        return ExtractionValidationResponse(
            extraction_id=extraction_row.id,
            document_name=mask_pans_in_text(document.file_name),
            document_type=document.document_type,
            preview_url=preview_url,
            fields=response_extraction,
            issues=issues,
            is_confirmed=extraction_row.confirmed_at is not None,
        )

    async def confirm(
        self,
        user: User,
        extraction_id: UUID,
        request: ConfirmExtractionRequest,
    ) -> ConfirmExtractionResponse:
        extraction_row, document = await self._get_record(user, extraction_id)
        extraction = self._parse_extraction(extraction_row, document)
        payload = extraction.model_dump(mode="json")
        for field_name, value in request.field_values.items():
            if field_name in type(extraction).model_fields:
                current = payload.get(field_name)
                if isinstance(current, dict) and "value" in current:
                    current["value"] = value
                    continue
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"{field_name} is not an editable extracted value.",
                )
            parts = field_name.split(".")
            if (
                isinstance(extraction, Form16Extraction)
                and len(parts) == 3
                and parts[0] == "deduction_items"
                and parts[2] in {"section", "amount"}
                and parts[1].isdigit()
            ):
                deduction_index = int(parts[1])
                deductions = payload.get("deduction_items")
                if isinstance(deductions, list) and deduction_index < len(deductions):
                    deduction = deductions[deduction_index]
                else:
                    deduction = None
                if isinstance(deduction, dict):
                    if parts[2] == "section" and value is not None:
                        deduction["section"] = value
                        continue
                    if parts[2] == "amount" and isinstance(deduction.get("amount"), dict):
                        deduction["amount"]["value"] = value
                        continue
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="One or more edited fields are not part of this extraction.",
            )
        pan_field = payload.get("employee_pan")
        if isinstance(pan_field, dict) and isinstance(pan_field.get("value"), str):
            pan_field["value"] = mask_pan(pan_field["value"])
        try:
            confirmed_extraction = type(extraction).model_validate(payload)
        except ValidationError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Corrected document values do not match the extraction schema.",
            ) from error

        issues = validation_issues(
            confirmed_extraction,
            confidence_threshold=self.settings.validation_low_confidence_threshold,
            section_80c_cap=self._verified_80c_cap(confirmed_extraction),
        )
        if any(issue.severity == "error" for issue in issues):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Resolve required or inconsistent fields before confirming.",
            )

        confirmed_at = datetime.now(UTC)
        extraction_row.payload = confirmed_extraction.model_dump(mode="json")
        extraction_row.confirmed_profile = request.profile.model_dump(mode="json")
        extraction_row.confirmed_at = confirmed_at
        confirmed_user = await UserRepository(self.session).get_by_id(user.id)
        if confirmed_user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account is unavailable.",
            )
        confirmed_user.confirmed_profile = request.profile.model_dump(mode="json")
        confirmed_user.profile_confirmed_at = confirmed_at
        await self.session.commit()
        await self.session.refresh(extraction_row)
        return ConfirmExtractionResponse(
            extraction_id=extraction_row.id,
            fields=self._masked_extraction(confirmed_extraction),
            profile=request.profile,
            confirmed_at=confirmed_at,
            issues=issues,
        )

    async def _get_record(
        self, user: User, extraction_id: UUID
    ) -> tuple[ExtractionResult, Document]:
        record = await self.repository.get_extraction_for_user(extraction_id, user.id)
        if record is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Extraction not found.",
            )
        extraction_row, document = record
        if document.status != "extracted":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Extraction is not ready for verification.",
            )
        return extraction_row, document

    @staticmethod
    def _parse_extraction(
        extraction_row: ExtractionResult, document: Document
    ) -> Form16Extraction | SalarySlipExtraction:
        extraction_model = (
            Form16Extraction if document.document_type == "form16" else SalarySlipExtraction
        )
        return extraction_model.model_validate(extraction_row.payload)

    @staticmethod
    def _masked_extraction(
        extraction: Form16Extraction | SalarySlipExtraction,
    ) -> Form16Extraction | SalarySlipExtraction:
        if not isinstance(extraction, Form16Extraction):
            return extraction
        pan_field = extraction.employee_pan
        return extraction.model_copy(
            update={
                "employee_pan": pan_field.model_copy(update={"value": mask_pan(pan_field.value)})
            }
        )

    def _verified_80c_cap(
        self, extraction: Form16Extraction | SalarySlipExtraction
    ) -> Decimal | None:
        if not isinstance(extraction, Form16Extraction):
            return None
        assessment_year = extraction.assessment_year.value
        financial_year = financial_year_for_assessment_year(assessment_year)
        if financial_year is None:
            return None
        try:
            rules = load_rules(
                financial_year,
                path=self.settings.tax_rules_file or RULES_FILE,
            )
        except RuleConfigurationError:
            return None
        cap = rules.regimes["old"].deductions["80C"].limit
        if (
            cap.status != "verified"
            or cap.value is None
            or cap.source_url is None
            or not is_official_source(cap.source_url.host)
            or cap.effective_from is None
        ):
            return None
        return cap.value
