from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictStr, field_validator

from app.schemas.extraction import (
    Form16Extraction,
    SalarySlipExtraction,
)
from app.schemas.tax import ConfirmedTaxpayerProfile


class ValidationModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ValidationIssue(ValidationModel):
    severity: Literal["error", "warning", "info"]
    field: str
    message: str
    suggested_fix: str


class ExtractionValidationResponse(ValidationModel):
    extraction_id: UUID
    document_name: str
    document_type: Literal["form16", "salary_slip"]
    preview_url: str
    fields: Form16Extraction | SalarySlipExtraction
    issues: list[ValidationIssue]
    is_confirmed: bool


class ConfirmExtractionRequest(ValidationModel):
    field_values: dict[str, StrictStr | None] = Field(default_factory=dict)
    profile: ConfirmedTaxpayerProfile
    consent_given: bool

    @field_validator("consent_given")
    @classmethod
    def require_consent(cls, value: bool) -> bool:
        if not value:
            raise ValueError("Consent is required before confirming extracted information.")
        return value


class ConfirmExtractionResponse(ValidationModel):
    extraction_id: UUID
    fields: Form16Extraction | SalarySlipExtraction
    profile: ConfirmedTaxpayerProfile
    confirmed_at: datetime
    issues: list[ValidationIssue]
