from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.suggestions import SuggestionResponse
from app.schemas.tax import (
    ConfirmedTaxpayerProfile,
    Money,
    TaxComparisonResult,
    TaxpayerProfile,
    TaxResult,
    TraceStep,
)


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class UserResponse(ApiModel):
    id: UUID
    email: str | None
    display_name: str | None
    preferred_financial_year: str | None
    confirmed_profile: ConfirmedTaxpayerProfile | None
    profile_confirmed_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class UpdateUserRequest(ApiModel):
    display_name: str | None = Field(default=None, max_length=200)
    preferred_financial_year: str | None = Field(default=None, max_length=20)


class DeleteMyDataRequest(ApiModel):
    confirmation: Literal["DELETE"]


class DocumentCreateRequest(ApiModel):
    file_name: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=120)
    size_bytes: int = Field(gt=0, le=50 * 1024 * 1024)

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "file_name": "form-16.pdf",
                    "content_type": "application/pdf",
                    "size_bytes": 245760,
                }
            ]
        }
    )


class DocumentResponse(ApiModel):
    id: UUID
    file_name: str
    content_type: str
    size_bytes: int
    document_type: str
    status: str
    scan_status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class TaxComputeRequest(ApiModel):
    financial_year: str = Field(min_length=1, max_length=20, examples=["2025-26"])
    regime: Literal["old", "new"] = Field(examples=["new"])
    profile: TaxpayerProfile


class TaxCompareRequest(ApiModel):
    financial_year: str = Field(min_length=1, max_length=20, examples=["2025-26"])
    profile: TaxpayerProfile


class TaxComputeResponse(ApiModel):
    id: UUID
    result: TaxResult


class TaxCompareResponse(ApiModel):
    id: UUID
    result: TaxComparisonResult


class TaxSimulationChange(ApiModel):
    kind: Literal["deduction", "rent"]
    amount: Money
    section: Literal["80C", "80D", "80CCD(1B)", "80E", "24B"] | None = None

    @model_validator(mode="after")
    def validate_change(self):
        if self.kind == "deduction" and self.section is None:
            raise ValueError("A deduction section is required for deduction simulations.")
        if self.kind == "rent" and self.section is not None:
            raise ValueError("A deduction section is not accepted for rent simulations.")
        return self


class TaxSimulationRequest(ApiModel):
    financial_year: str = Field(min_length=1, max_length=20)
    profile: TaxpayerProfile
    change: TaxSimulationChange


class TaxSimulationResponse(ApiModel):
    financial_year: str
    rules_version: str
    before: TaxComparisonResult
    after: TaxComparisonResult
    tax_saved: Money
    recommended_regime_changed: bool
    trace_before: list[TraceStep]
    trace_after: list[TraceStep]


class TaxSuggestionsRequest(ApiModel):
    financial_year: str = Field(min_length=1, max_length=20)
    profile: ConfirmedTaxpayerProfile

    @model_validator(mode="after")
    def financial_year_matches_profile(self):
        if self.financial_year != self.profile.financial_year:
            raise ValueError("financial_year must match the confirmed profile.")
        return self


class TaxSuggestionsResponse(ApiModel):
    financial_year: str
    rules_version: str
    suggestions: list[SuggestionResponse]
    savings_potential: Money
    planned_count: int


class SuggestionPlanRequest(ApiModel):
    planned_to_do: bool


class SuggestionPlanResponse(ApiModel):
    id: UUID
    key: str
    planned_to_do: bool
