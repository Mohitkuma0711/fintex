from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.core.config import Settings
from app.core.pii import mask_pan, mask_pans_in_text
from app.schemas.tax import ConfirmedTaxpayerProfile
from app.services.reports.service import (
    DISCLAIMER,
    ReportService,
    _money,
    filing_guidance,
)


def _confirmed_profile() -> ConfirmedTaxpayerProfile:
    return ConfirmedTaxpayerProfile.model_validate(
        {
            "salary_components": {
                "basic_salary": "100000",
                "dearness_allowance": "0",
                "hra_received": "0",
                "other_allowances": "0",
            },
            "hra_inputs": {"rent_paid": "0"},
            "other_income": "0",
            "deductions_claimed": {
                "section_80c": "0",
                "section_80d": "0",
                "section_80ccd_1b": "0",
                "section_80e": "0",
                "section_24b": "0",
            },
            "age_bracket": "below_60",
            "city_type": "non_metro",
            "employment_type": "employee",
            "consent_given": True,
            "financial_year": "2025-26",
            "planning_eligibility": {
                "health_insurance_eligible": False,
                "eligible_health_insurance_premium": "0",
                "education_loan_eligible": False,
                "eligible_education_loan_interest": "0",
                "home_loan_eligible": False,
                "eligible_home_loan_interest": "0",
            },
        }
    )


def test_indian_money_formatting_and_filing_guidance_are_non_binding() -> None:
    assert _money("142300.00") == "INR 1,42,300"
    guidance = filing_guidance(_confirmed_profile())
    assert guidance["status"] == "guidance_only"
    assert guidance["likely_forms"] == ["ITR-1", "ITR-2"]
    assert "candidate forms" in guidance["guidance"]
    assert guidance["prefilled_summary"]["financial_year"] == "2025-26"
    assert guidance["disclaimer"] == DISCLAIMER


def test_pan_is_masked_in_fields_and_filename_text() -> None:
    assert mask_pan("ABCDE1234F") == "AB*******F"
    assert mask_pan(None) is None
    assert mask_pan("not-a-pan") == "[MASKED]"
    assert mask_pans_in_text("form-ABCDE1234F.pdf") == "form-AB*******F.pdf"


def test_filing_guidance_without_profile_does_not_recommend_a_form() -> None:
    guidance = filing_guidance(None)
    assert guidance["status"] == "profile_required"
    assert guidance["likely_forms"] == []
    assert guidance["prefilled_summary"] is None


@pytest.mark.asyncio
async def test_report_pdf_contains_a_saved_comparison(monkeypatch: pytest.MonkeyPatch) -> None:
    service = ReportService(session=None)  # type: ignore[arg-type]
    computation = SimpleNamespace(
        id=uuid4(),
        financial_year="2025-26",
        rules_version="synthetic-rules",
        created_at=datetime.now(UTC),
        result={
            "old_regime": {
                "taxable_income": "100000",
                "total_tax": "1000",
                "trace": [
                    {
                        "label": "Taxable income",
                        "formula": "gross - deductions",
                        "output": "100000",
                        "plain_language_why": "Synthetic test trace.",
                        "rule_reference": "synthetic",
                    }
                ],
            },
            "new_regime": {
                "taxable_income": "110000",
                "total_tax": "1200",
                "trace": [],
            },
            "recommended_regime": "old",
            "saving": "200",
        },
    )

    async def latest_comparison(_user_id):
        return computation, []

    monkeypatch.setattr(service, "latest_comparison", latest_comparison)
    pdf = await service.build_pdf(uuid4())
    assert pdf is not None
    assert pdf.startswith(b"%PDF")


def test_production_settings_reject_http_or_wildcard_cors_and_long_signed_urls() -> None:
    with pytest.raises(ValueError, match="explicit"):
        Settings(cors_origins=["*"])
    with pytest.raises(ValueError, match="HTTPS"):
        Settings(app_env="production", cors_origins=["http://example.test"])
    with pytest.raises(ValueError, match="between 60 and 900"):
        Settings(storage_signed_url_ttl_seconds=901)
