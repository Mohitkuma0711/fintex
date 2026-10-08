from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.schemas.tax import ConfirmedTaxpayerProfile, TaxComparisonResult, TaxpayerProfile
from app.services.tax_engine.compare import compare_regimes
from app.services.tax_engine.rules import RulesetVersion, SuggestionTerms

ZERO = Decimal("0")
SECTION_TO_PROFILE_FIELD = {
    "80C": "section_80c",
    "80D": "section_80d",
    "80CCD(1B)": "section_80ccd_1b",
    "80E": "section_80e",
    "24B": "section_24b",
}


class SuggestionDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str
    title: str
    product: str
    amount_to_invest: Decimal
    lock_in_period: str
    liquidity_note: str
    tax_saved: Decimal
    net_benefit: Decimal
    eligible_regime: Literal["old", "new"] | None
    alternative_group: str | None
    rule_reference: str
    explanation: str
    explanation_source: Literal["gemini", "template"]
    before: TaxComparisonResult
    after: TaxComparisonResult


def _claimed(profile: TaxpayerProfile, section: str) -> Decimal:
    field_name = SECTION_TO_PROFILE_FIELD[section]
    return getattr(profile.deductions_claimed, field_name)


def _deduction_room(profile: TaxpayerProfile, rules: RulesetVersion, section: str) -> Decimal:
    room = ZERO
    for regime in rules.regimes.values():
        deduction = regime.deductions[section]
        if deduction.enabled.value is not True:
            continue
        age_limit = deduction.limits_by_age.get(profile.age_bracket)
        selected_limit = age_limit if age_limit is not None else deduction.limit
        if selected_limit.value is None:
            continue
        already_allowed = min(_claimed(profile, section), selected_limit.value)
        room = max(room, selected_limit.value - already_allowed)
    return max(room, ZERO)


def _incremental_claim(
    profile: TaxpayerProfile,
    section: str,
    amount: Decimal,
) -> TaxpayerProfile:
    values = profile.model_dump(mode="python")
    profile_field = SECTION_TO_PROFILE_FIELD[section]
    values["deductions_claimed"][profile_field] = _claimed(profile, section) + amount
    return TaxpayerProfile.model_validate(values)


def _rule_reference(
    comparison: TaxComparisonResult,
    section: str | None,
) -> str:
    result = (
        comparison.old_regime if comparison.recommended_regime == "old" else comparison.new_regime
    )
    expected_label = "HRA exemption" if section is None else f"{section} deduction"
    for step in result.trace:
        if step.label == expected_label:
            return step.rule_reference
    raise ValueError(f"The tax trace does not contain the expected step {expected_label!r}.")


def _eligible_expense(profile: ConfirmedTaxpayerProfile, section: str) -> Decimal | None:
    eligibility = profile.planning_eligibility
    if section == "80D" and eligibility.health_insurance_eligible:
        return eligibility.eligible_health_insurance_premium
    if section == "80E" and eligibility.education_loan_eligible:
        return eligibility.eligible_education_loan_interest
    if section == "24B" and eligibility.home_loan_eligible:
        return eligibility.eligible_home_loan_interest
    return None


def build_suggestion_drafts(
    confirmed_profile: ConfirmedTaxpayerProfile,
    rules: RulesetVersion,
) -> list[SuggestionDraft]:
    rules.require_ready()
    rules.require_suggestion_terms_ready()
    profile = confirmed_profile.to_taxpayer_profile()
    before = compare_regimes(profile, rules)
    candidates: list[tuple[str, str, Decimal]] = [
        (key, section, _deduction_room(profile, rules, section))
        for key, section in (
            ("80C_ELSS", "80C"),
            ("80C_PPF", "80C"),
            ("80CCD(1B)", "80CCD(1B)"),
        )
    ]
    for key, section in (("80D", "80D"), ("80E", "80E"), ("24B", "24B")):
        eligible_total = _eligible_expense(confirmed_profile, section)
        if eligible_total is None:
            continue
        current_claim = _claimed(profile, section)
        available_qualifying_expense = max(ZERO, eligible_total - current_claim)
        candidates.append(
            (
                key,
                section,
                min(_deduction_room(profile, rules, section), available_qualifying_expense),
            )
        )

    drafts: list[SuggestionDraft] = []
    for key, section, investment_amount in candidates:
        if investment_amount <= ZERO:
            continue
        after_profile = _incremental_claim(profile, section, investment_amount)
        after = compare_regimes(after_profile, rules)
        tax_saved = max(
            ZERO,
            min(before.old_regime.total_tax, before.new_regime.total_tax)
            - min(after.old_regime.total_tax, after.new_regime.total_tax),
        )
        if tax_saved <= ZERO:
            continue
        terms: SuggestionTerms = rules.suggestion_terms[key]
        drafts.append(
            SuggestionDraft(
                key=key,
                title=terms.title,
                product=terms.title,
                amount_to_invest=investment_amount,
                lock_in_period=terms.lock_in_period or "",
                liquidity_note=terms.liquidity_note or "",
                tax_saved=tax_saved,
                net_benefit=tax_saved,
                eligible_regime=after.recommended_regime,
                alternative_group="80C" if section == "80C" else None,
                rule_reference=_rule_reference(before, section),
                explanation=(
                    f"Adding this eligible amount changes the engine's lowest regime tax "
                    f"from {min(before.old_regime.total_tax, before.new_regime.total_tax)} to "
                    f"{min(after.old_regime.total_tax, after.new_regime.total_tax)}. "
                    "Net benefit is tax saved only; investment returns, fees, and opportunity "
                    "cost are not estimated."
                ),
                explanation_source="template",
                before=before,
                after=after,
            )
        )

    if profile.salary_components.hra_received > ZERO and profile.hra_inputs.rent_paid > ZERO:
        hra_terms = rules.suggestion_terms["HRA"]
        eligible_hra = [
            regime_name
            for regime_name, regime in rules.regimes.items()
            if regime.hra.enabled.value is True
        ]
        hra_regime = "old" if "old" in eligible_hra else (eligible_hra[0] if eligible_hra else None)
        hra_after = before
        if hra_regime is not None:
            hra_result = before.old_regime if hra_regime == "old" else before.new_regime
        else:
            hra_result = None
        if hra_result is not None:
            hra_step = next(step for step in hra_result.trace if step.label == "HRA exemption")
            drafts.append(
                SuggestionDraft(
                    key="HRA",
                    title=hra_terms.title,
                    product=hra_terms.title,
                    amount_to_invest=ZERO,
                    lock_in_period=hra_terms.lock_in_period or "",
                    liquidity_note=hra_terms.liquidity_note or "",
                    tax_saved=ZERO,
                    net_benefit=ZERO,
                    eligible_regime=hra_regime,
                    alternative_group=None,
                    rule_reference=hra_step.rule_reference,
                    explanation=(
                        "The confirmed rent is already included in the engine's HRA calculation "
                        f"for the {hra_regime} regime. No additional saving is projected without "
                        "a different rent amount supported by the taxpayer's actual records."
                    ),
                    explanation_source="template",
                    before=before,
                    after=hra_after,
                )
            )

    return sorted(drafts, key=lambda item: (-item.net_benefit, item.key))


def savings_potential(drafts: list[SuggestionDraft]) -> Decimal:
    alternatives: dict[str, Decimal] = {}
    total = ZERO
    for draft in drafts:
        if draft.alternative_group is None:
            total += draft.net_benefit
        else:
            alternatives[draft.alternative_group] = max(
                alternatives.get(draft.alternative_group, ZERO),
                draft.net_benefit,
            )
    return total + sum(alternatives.values(), ZERO)


def apply_simulation_change(
    profile: TaxpayerProfile,
    *,
    kind: Literal["deduction", "rent"],
    amount: Decimal,
    section: str | None,
) -> TaxpayerProfile:
    if kind == "rent":
        values = profile.model_dump(mode="python")
        values["hra_inputs"]["rent_paid"] = amount
        return TaxpayerProfile.model_validate(values)
    if section is None or section not in SECTION_TO_PROFILE_FIELD:
        raise ValueError("A supported deduction section is required.")
    return _incremental_claim(profile, section, amount)


def tax_difference(before: TaxComparisonResult, after: TaxComparisonResult) -> Decimal:
    before_best = min(before.old_regime.total_tax, before.new_regime.total_tax)
    after_best = min(after.old_regime.total_tax, after.new_regime.total_tax)
    return before_best - after_best
