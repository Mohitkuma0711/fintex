import re
from decimal import Decimal, InvalidOperation
from typing import Any

from app.schemas.extraction import Form16Extraction, SalarySlipExtraction
from app.schemas.validation import ValidationIssue

_ASSESSMENT_YEAR = re.compile(r"(?<!\d)(\d{4})[-/](\d{2,4})(?!\d)")
_AMOUNT_CLEANUP = re.compile(r"[₹,\s]")


def _money(value: str | None) -> Decimal | None:
    if value is None:
        return None
    normalized = _AMOUNT_CLEANUP.sub("", value)
    try:
        amount = Decimal(normalized)
    except InvalidOperation:
        return None
    return amount if amount.is_finite() else None


def _field_value(fields: dict[str, Any], name: str) -> str | None:
    field = fields.get(name)
    return field.get("value") if isinstance(field, dict) else None


def validation_issues(
    extraction: Form16Extraction | SalarySlipExtraction,
    *,
    confidence_threshold: Decimal,
    section_80c_cap: Decimal | None = None,
) -> list[ValidationIssue]:
    fields = extraction.model_dump(mode="python")
    issues: list[ValidationIssue] = []

    for name, value in fields.items():
        if isinstance(value, dict):
            text = value.get("value")
            confidence = value.get("confidence")
            if text is not None and confidence < confidence_threshold:
                issues.append(
                    ValidationIssue(
                        severity="warning",
                        field=name,
                        message=f"Extraction confidence is below {confidence_threshold}.",
                        suggested_fix=(
                            "Compare this value with the source document and correct it if needed."
                        ),
                    )
                )

    for index, deduction in enumerate(getattr(extraction, "deduction_items", [])):
        if (
            deduction.amount.value is not None
            and deduction.amount.confidence < confidence_threshold
        ):
            issues.append(
                ValidationIssue(
                    severity="warning",
                    field=f"deduction_items.{index}.amount",
                    message=f"Extraction confidence is below {confidence_threshold}.",
                    suggested_fix="Compare this deduction amount with the source document.",
                )
            )

    if isinstance(extraction, Form16Extraction):
        required = ("employee_name", "employee_pan", "assessment_year", "gross_salary")
        gross_name = "gross_salary"
        tds_name = "total_tax_deducted"
    else:
        required = ("employee_name", "pay_period", "gross_pay", "net_pay", "basic_salary")
        gross_name = "gross_pay"
        tds_name = ""

    for name in required:
        if _field_value(fields, name) is None or not _field_value(fields, name).strip():
            issues.append(
                ValidationIssue(
                    severity="error",
                    field=name,
                    message="A required document value is missing.",
                    suggested_fix="Enter this value from the source document before confirming.",
                )
            )

    gross = _money(_field_value(fields, gross_name))
    if isinstance(extraction, SalarySlipExtraction):
        component_names = ("basic_salary", "dearness_allowance", "hra", "other_earnings")
        component_values = [_money(_field_value(fields, name)) for name in component_names]
        for name in (*component_names, gross_name, "net_pay", "deductions"):
            amount_text = _field_value(fields, name)
            amount = _money(amount_text)
            if amount_text and (amount is None or amount < 0):
                issues.append(
                    ValidationIssue(
                        severity="warning",
                        field=name,
                        message="This value is not a readable non-negative amount.",
                        suggested_fix="Enter the amount exactly as shown on the salary slip.",
                    )
                )
        if gross is not None and all(value is not None for value in component_values):
            component_total = sum(
                (value for value in component_values if value is not None),
                start=Decimal("0"),
            )
            if gross != component_total:
                issues.append(
                    ValidationIssue(
                        severity="error",
                        field="gross_pay",
                        message="Gross pay does not equal the sum of the listed earnings.",
                        suggested_fix=(
                            "Check gross pay and each salary component against the payslip."
                        ),
                    )
                )

    if tds_name:
        tds_text = _field_value(fields, tds_name)
        tds = _money(tds_text)
        if tds_text and (tds is None or tds < 0):
            issues.append(
                ValidationIssue(
                    severity="warning",
                    field=tds_name,
                    message="Tax deducted at source is not a readable non-negative amount.",
                    suggested_fix="Enter the TDS amount as shown on the document.",
                )
            )
        elif tds is not None and gross is not None and tds > gross:
            issues.append(
                ValidationIssue(
                    severity="error",
                    field=tds_name,
                    message=("TDS exceeds gross salary, inconsistent with extracted amounts."),
                    suggested_fix="Recheck TDS and gross salary against the source document.",
                )
            )

    if isinstance(extraction, Form16Extraction):
        section_80c = _money(extraction.section_80c.value)
        if section_80c is None:
            extracted_80c_items = [
                _money(item.amount.value)
                for item in extraction.deduction_items
                if re.sub(r"[^a-z0-9]", "", item.section.lower()) == "80c"
            ]
            if extracted_80c_items and all(item is not None for item in extracted_80c_items):
                section_80c = sum(
                    (item for item in extracted_80c_items if item is not None),
                    start=Decimal("0"),
                )
        if section_80c is not None:
            if section_80c_cap is None:
                issues.append(
                    ValidationIssue(
                        severity="info",
                        field="section_80c",
                        message="A verified 80C limit is not available for this assessment year.",
                        suggested_fix=(
                            "Check official rules for the relevant year; do not rely on an "
                            "unverified limit."
                        ),
                    )
                )
            elif section_80c > section_80c_cap:
                issues.append(
                    ValidationIssue(
                        severity="warning",
                        field="section_80c",
                        message=(
                            "The extracted 80C total exceeds the verified limit for this "
                            "assessment year."
                        ),
                        suggested_fix=(
                            "Check the amount and eligible 80C items against the official limit."
                        ),
                    )
                )

        seen_sections: set[str] = set()
        for deduction in extraction.deduction_items:
            section = re.sub(r"[^a-z0-9]", "", deduction.section.lower())
            if section in seen_sections:
                issues.append(
                    ValidationIssue(
                        severity="warning",
                        field="deduction_items",
                        message=(
                            f"Section {deduction.section} appears more than once in extracted "
                            "deductions."
                        ),
                        suggested_fix=(
                            "Check whether the entries are separate eligible items or a duplicate."
                        ),
                    )
                )
            seen_sections.add(section)

    return issues


def financial_year_for_assessment_year(assessment_year: str | None) -> str | None:
    if assessment_year is None:
        return None
    match = _ASSESSMENT_YEAR.search(assessment_year)
    if match is None:
        return None
    assessment_start = int(match.group(1))
    return f"FY {assessment_start - 1}-{str(assessment_start)[-2:]}"
