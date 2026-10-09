from decimal import Decimal, InvalidOperation
from html import escape
from io import BytesIO
from typing import Any
from uuid import UUID

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Suggestion, TaxComputation
from app.schemas.tax import ConfirmedTaxpayerProfile

DISCLAIMER = "FinTax AI provides guidance, not professional tax advice. It does not file returns."
OFFICIAL_FILING_HELP = "https://www.incometax.gov.in/iec/foportal/help/individual"


def _money(value: object) -> str:
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return "Not available"
    sign = "-" if amount < 0 else ""
    whole, dot, fraction = format(abs(amount), "f").partition(".")
    if len(whole) > 3:
        last = whole[-3:]
        remaining = whole[:-3]
        groups: list[str] = []
        while remaining:
            groups.insert(0, remaining[-2:])
            remaining = remaining[:-2]
        whole = ",".join([*groups, last])
    return f"INR {sign}{whole}{dot}{fraction.rstrip('0') if dot else ''}".rstrip(".")


def _safe_text(value: object) -> str:
    if value is None:
        return "Not available"
    return escape(str(value)).replace("\n", "<br/>")


class ReportService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def latest_comparison(
        self,
        user_id: UUID,
    ) -> tuple[TaxComputation | None, list[Suggestion]]:
        computation = (
            await self.session.execute(
                select(TaxComputation)
                .where(
                    TaxComputation.user_id == user_id,
                    TaxComputation.computation_type == "compare",
                    TaxComputation.deleted_at.is_(None),
                )
                .order_by(TaxComputation.created_at.desc(), TaxComputation.id.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if computation is None:
            return None, []
        suggestions = list(
            (
                await self.session.execute(
                    select(Suggestion)
                    .where(
                        Suggestion.user_id == user_id,
                        Suggestion.financial_year == computation.financial_year,
                        Suggestion.rules_version == computation.rules_version,
                        Suggestion.deleted_at.is_(None),
                    )
                    .order_by(Suggestion.created_at, Suggestion.id)
                )
            )
            .scalars()
            .all()
        )
        suggestions.sort(
            key=lambda row: Decimal(str(row.detail.get("net_benefit", "0"))),
            reverse=True,
        )
        return computation, suggestions

    async def build_pdf(self, user_id: UUID) -> bytes | None:
        computation, suggestions = await self.latest_comparison(user_id)
        if computation is None:
            return None
        result = computation.result
        output = BytesIO()
        document = SimpleDocTemplate(
            output,
            pagesize=A4,
            rightMargin=18 * mm,
            leftMargin=18 * mm,
            topMargin=18 * mm,
            bottomMargin=18 * mm,
            title="FinTax AI tax summary",
            author="FinTax AI",
        )
        base_styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "FinTaxTitle",
            parent=base_styles["Title"],
            alignment=TA_CENTER,
            textColor=colors.HexColor("#102345"),
            spaceAfter=8 * mm,
        )
        heading_style = ParagraphStyle(
            "FinTaxHeading",
            parent=base_styles["Heading2"],
            textColor=colors.HexColor("#155eef"),
            spaceBefore=5 * mm,
            spaceAfter=2 * mm,
        )
        body_style = base_styles["BodyText"]
        story: list[Any] = [
            Paragraph("FinTax AI · Tax summary", title_style),
            Paragraph(f"Financial year: {_safe_text(computation.financial_year)}", body_style),
            Paragraph(f"Rules version: {_safe_text(computation.rules_version)}", body_style),
            Spacer(1, 4 * mm),
        ]
        old = result.get("old_regime", {})
        new = result.get("new_regime", {})
        comparison = [
            ["Regime", "Taxable income", "Total tax"],
            ["Old", _money(old.get("taxable_income")), _money(old.get("total_tax"))],
            ["New", _money(new.get("taxable_income")), _money(new.get("total_tax"))],
        ]
        comparison_table = Table(comparison, colWidths=[45 * mm, 60 * mm, 55 * mm])
        comparison_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8efff")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#102345")),
                    ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#ccd5e3")),
                    ("PADDING", (0, 0), (-1, -1), 7),
                ]
            )
        )
        recommended = result.get("recommended_regime", "Unavailable")
        story.extend(
            [
                Paragraph("Regime comparison", heading_style),
                comparison_table,
                Spacer(1, 3 * mm),
                Paragraph(
                    f"Recommended by the saved engine comparison: {_safe_text(recommended)}. "
                    f"Difference reported by the engine: "
                    f"{_money(result.get('saving'))}.",
                    body_style,
                ),
            ]
        )
        story.append(Paragraph("Top saved suggestions", heading_style))
        if suggestions:
            for suggestion in suggestions[:5]:
                detail = suggestion.detail
                story.append(
                    Paragraph(
                        f"<b>{_safe_text(suggestion.title)}</b><br/>"
                        f"Potential tax impact: {_money(detail.get('tax_saved'))}; "
                        f"amount to invest: {_money(detail.get('amount_to_invest'))}.<br/>"
                        f"{_safe_text(detail.get('explanation'))}",
                        body_style,
                    )
                )
                story.append(Spacer(1, 2 * mm))
        else:
            story.append(Paragraph("No saved suggestions are available.", body_style))

        story.append(Paragraph("Calculation trace appendix", heading_style))
        for regime_name, regime_result in (("Old regime", old), ("New regime", new)):
            story.append(Paragraph(_safe_text(regime_name), base_styles["Heading3"]))
            trace = regime_result.get("trace", [])
            if not isinstance(trace, list) or not trace:
                story.append(Paragraph("No trace was saved for this regime.", body_style))
                continue
            for step in trace:
                if not isinstance(step, dict):
                    continue
                story.append(
                    KeepTogether(
                        [
                            Paragraph(
                                f"<b>{_safe_text(step.get('label'))}</b> — "
                                f"{_money(step.get('output'))}",
                                body_style,
                            ),
                            Paragraph(
                                f"Formula: {_safe_text(step.get('formula'))}<br/>"
                                f"Why: {_safe_text(step.get('plain_language_why'))}<br/>"
                                f"Rule: {_safe_text(step.get('rule_reference'))}",
                                base_styles["Italic"],
                            ),
                            Spacer(1, 2 * mm),
                        ]
                    )
                )
        story.extend(
            [
                Spacer(1, 5 * mm),
                Paragraph(_safe_text(DISCLAIMER), base_styles["Italic"]),
            ]
        )
        document.build(story)
        return output.getvalue()


def filing_guidance(profile: ConfirmedTaxpayerProfile | None) -> dict[str, Any]:
    if profile is None:
        return {
            "status": "profile_required",
            "likely_forms": [],
            "guidance": (
                "Confirm your income profile before considering an ITR form. "
                "The official filing portal determines form eligibility."
            ),
            "schedules_to_review": [],
            "documents_to_prepare": [],
            "prefilled_summary": None,
            "official_source": OFFICIAL_FILING_HELP,
            "disclaimer": DISCLAIMER,
        }

    employee = profile.employment_type == "employee"
    forms = ["ITR-1", "ITR-2"] if employee else ["ITR-3", "ITR-4"]
    schedule_names = ["Personal information", "Salary or business/profession income"]
    if profile.other_income != 0:
        schedule_names.append("Other income")
    if any(profile.deductions_claimed.as_mapping().values()):
        schedule_names.append("Deductions and tax relief")
    schedule_names.extend(["Tax deducted at source", "Bank account and refund details"])
    documents = [
        "Form 16 or salary statements, if applicable",
        "Annual tax statement / Form 26AS and AIS",
        "Proofs supporting deductions or exemptions you intend to claim",
        "Bank account details and interest statements",
        "Prior-year return and brought-forward loss details, if applicable",
    ]
    summary = {
        "financial_year": profile.financial_year,
        "employment_type": profile.employment_type,
        "salary_components": profile.salary_components.model_dump(mode="json"),
        "other_income": str(profile.other_income),
        "deductions_claimed": {
            key: str(value) for key, value in profile.deductions_claimed.as_mapping().items()
        },
        "hra_inputs": profile.hra_inputs.model_dump(mode="json"),
        "age_bracket": profile.age_bracket,
        "city_type": profile.city_type,
        "note": (
            "These are user-confirmed inputs, not a completed return. "
            "Verify amounts and eligibility on the official filing portal."
        ),
    }
    return {
        "status": "guidance_only",
        "likely_forms": forms,
        "guidance": (
            "These are candidate forms based only on the recorded employment category. "
            "This profile does not capture all eligibility conditions or income types. "
            "Use the official portal's current form guidance before selecting a form."
        ),
        "schedules_to_review": schedule_names,
        "documents_to_prepare": documents,
        "prefilled_summary": summary,
        "official_source": OFFICIAL_FILING_HELP,
        "disclaimer": DISCLAIMER,
    }
