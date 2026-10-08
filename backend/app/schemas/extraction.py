from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

Confidence = Annotated[Decimal, Field(ge=Decimal("0"), le=Decimal("1"))]
PageNumber = Annotated[int, Field(ge=1)]


class ExtractionModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ExtractedField(ExtractionModel):
    value: str | None = Field(
        default=None,
        max_length=500,
        description="Text exactly supported by the source document; null if absent or unclear.",
    )
    confidence: Confidence = Field(description="Confidence from 0 to 1 based only on visible text.")
    source_page: PageNumber | None = Field(
        description="One-based page where this value is visible; null if unknown."
    )


class ExtractedDeduction(ExtractionModel):
    section: str = Field(min_length=1, max_length=32)
    amount: ExtractedField


class Form16Extraction(ExtractionModel):
    employee_name: ExtractedField
    employee_pan: ExtractedField
    employer_name: ExtractedField
    employer_tan: ExtractedField
    assessment_year: ExtractedField
    gross_salary: ExtractedField
    exempt_allowances: ExtractedField
    perquisites: ExtractedField
    profits_in_lieu_of_salary: ExtractedField
    deductions_under_chapter_vi_a: ExtractedField
    section_80c: ExtractedField = Field(
        default_factory=lambda: ExtractedField(
            value=None, confidence=Decimal("0"), source_page=None
        )
    )
    deduction_items: list[ExtractedDeduction] = Field(default_factory=list)
    taxable_income: ExtractedField
    total_tax_deducted: ExtractedField


class SalarySlipExtraction(ExtractionModel):
    employee_name: ExtractedField
    employee_id: ExtractedField
    employer_name: ExtractedField
    pay_period: ExtractedField
    basic_salary: ExtractedField
    dearness_allowance: ExtractedField
    hra: ExtractedField
    other_earnings: ExtractedField
    gross_pay: ExtractedField
    deductions: ExtractedField
    net_pay: ExtractedField


class DocumentUploadResponse(ExtractionModel):
    id: UUID
    file_name: str
    content_type: str
    size_bytes: int
    document_type: str
    status: str
    scan_status: str
    signed_url: str
    signed_url_expires_in: int


class DocumentExtractionResponse(ExtractionModel):
    id: UUID
    extraction_id: UUID | None = None
    file_name: str
    document_type: str
    status: str
    scan_status: str
    extraction: Form16Extraction | SalarySlipExtraction | None = None
    error_code: str | None = None
