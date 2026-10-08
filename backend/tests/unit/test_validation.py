from decimal import Decimal

import pytest

from app.schemas.extraction import Form16Extraction, SalarySlipExtraction
from app.schemas.tax import ConfirmedTaxpayerProfile
from app.services.validation.checks import (
    financial_year_for_assessment_year,
    validation_issues,
)


def _with_source_pages(values: dict[str, object]) -> dict[str, object]:
    for value in values.values():
        if isinstance(value, dict) and "confidence" in value:
            value.setdefault("source_page", 1)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict) and isinstance(item.get("amount"), dict):
                    item["amount"].setdefault("source_page", 1)
    return values


def salary_slip(**overrides: object) -> SalarySlipExtraction:
    values: dict[str, object] = {
        "employee_name": {"value": "Synthetic Employee", "confidence": "0.99"},
        "employee_id": {"value": "TEST-1", "confidence": "0.99"},
        "employer_name": {"value": "Synthetic Employer", "confidence": "0.99"},
        "pay_period": {"value": "April 2025", "confidence": "0.99"},
        "basic_salary": {"value": "50000", "confidence": "0.99"},
        "dearness_allowance": {"value": "0", "confidence": "0.99"},
        "hra": {"value": "10000", "confidence": "0.99"},
        "other_earnings": {"value": "5000", "confidence": "0.99"},
        "gross_pay": {"value": "65000", "confidence": "0.99"},
        "deductions": {"value": "1000", "confidence": "0.99"},
        "net_pay": {"value": "64000", "confidence": "0.99"},
    }
    values.update(overrides)
    return SalarySlipExtraction.model_validate(_with_source_pages(values))


def form16(**overrides: object) -> Form16Extraction:
    values: dict[str, object] = {
        "employee_name": {"value": "Synthetic Employee", "confidence": "0.99"},
        "employee_pan": {"value": "ABCDE1234F", "confidence": "0.99"},
        "employer_name": {"value": "Synthetic Employer", "confidence": "0.99"},
        "employer_tan": {"value": "TEST00000A", "confidence": "0.99"},
        "assessment_year": {"value": "AY 2025-26", "confidence": "0.99"},
        "gross_salary": {"value": "65000", "confidence": "0.99"},
        "exempt_allowances": {"value": "0", "confidence": "0.99"},
        "perquisites": {"value": "0", "confidence": "0.99"},
        "profits_in_lieu_of_salary": {"value": "0", "confidence": "0.99"},
        "deductions_under_chapter_vi_a": {"value": "10000", "confidence": "0.99"},
        "total_tax_deducted": {"value": "1000", "confidence": "0.99"},
        "taxable_income": {"value": "55000", "confidence": "0.99"},
    }
    values.update(overrides)
    return Form16Extraction.model_validate(_with_source_pages(values))


def issue_fields(
    extraction: Form16Extraction | SalarySlipExtraction,
    *,
    threshold: Decimal = Decimal("0.8"),
    cap: Decimal | None = None,
) -> set[str]:
    return {
        issue.field
        for issue in validation_issues(
            extraction,
            confidence_threshold=threshold,
            section_80c_cap=cap,
        )
    }


def confirmed_profile(**overrides: object) -> ConfirmedTaxpayerProfile:
    payload: dict[str, object] = {
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
        "salary_components": {
            "basic_salary": "50000",
            "dearness_allowance": "0",
            "hra_received": "10000",
            "other_allowances": "5000",
        },
        "hra_inputs": {"rent_paid": "20000"},
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
    }
    payload.update(overrides)
    return ConfirmedTaxpayerProfile.model_validate(payload)


def test_salary_gross_must_equal_sum_of_earnings() -> None:
    assert "gross_pay" not in issue_fields(salary_slip())
    assert "gross_pay" in issue_fields(
        salary_slip(gross_pay={"value": "64000", "confidence": "0.99"})
    )


def test_tds_must_not_exceed_gross_salary() -> None:
    assert "total_tax_deducted" not in issue_fields(form16())
    assert "total_tax_deducted" in issue_fields(
        form16(total_tax_deducted={"value": "70000", "confidence": "0.99"})
    )


def test_80c_amount_is_compared_with_supplied_verified_cap() -> None:
    extraction = form16(section_80c={"value": "101", "confidence": "0.99"})
    assert "section_80c" in issue_fields(extraction, cap=Decimal("100"))
    assert "section_80c" not in issue_fields(extraction, cap=Decimal("101"))


def test_80c_is_not_compared_to_an_unverified_missing_cap() -> None:
    issues = validation_issues(
        form16(section_80c={"value": "101", "confidence": "0.99"}),
        confidence_threshold=Decimal("0.8"),
    )
    assert any(item.field == "section_80c" and item.severity == "info" for item in issues)


def test_duplicate_deduction_sections_are_flagged() -> None:
    result = form16(
        deduction_items=[
            {"section": "80C", "amount": {"value": "500", "confidence": "0.99"}},
            {"section": "80-C", "amount": {"value": "500", "confidence": "0.99"}},
        ]
    )
    assert "deduction_items" in issue_fields(result)


def test_missing_mandatory_fields_are_reported() -> None:
    result = form16(
        employee_name={"value": None, "confidence": "0"},
        employee_pan={"value": None, "confidence": "0"},
    )
    fields = issue_fields(result)
    assert {"employee_name", "employee_pan"} <= fields


def test_low_confidence_fields_are_reported_at_configured_threshold() -> None:
    result = form16(
        gross_salary={"value": "65000", "confidence": "0.7"},
    )
    assert "gross_salary" in issue_fields(result, threshold=Decimal("0.8"))
    assert "gross_salary" not in issue_fields(result, threshold=Decimal("0.7"))


@pytest.mark.parametrize(
    ("assessment_year", "financial_year"),
    [("AY 2025-26", "FY 2024-25"), ("2027/28", "FY 2026-27"), ("unknown", None)],
)
def test_assessment_year_is_mapped_to_financial_year(
    assessment_year: str, financial_year: str | None
) -> None:
    assert financial_year_for_assessment_year(assessment_year) == financial_year


def test_confirmed_profile_is_strict_and_converts_to_engine_profile() -> None:
    profile = confirmed_profile()
    assert profile.to_taxpayer_profile().salary_components.basic_salary == Decimal("50000")
    with pytest.raises(ValueError, match="decimal string"):
        confirmed_profile(other_income=1000)
    with pytest.raises(ValueError, match="Explicit consent"):
        confirmed_profile(consent_given=False)
