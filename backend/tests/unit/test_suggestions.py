from decimal import Decimal

from app.schemas.tax import ConfirmedTaxpayerProfile, TaxpayerProfile
from app.services.suggestions.engine import (
    apply_simulation_change,
    build_suggestion_drafts,
    savings_potential,
    tax_difference,
)
from app.services.tax_engine.compare import compare_regimes
from tests.unit.tax_engine_fixtures import build_test_rules, regime_rules


def _confirmed_profile(**overrides: object) -> ConfirmedTaxpayerProfile:
    values: dict[str, object] = {
        "employment_type": "employee",
        "consent_given": True,
        "financial_year": "2025-26",
        "salary_components": {
            "basic_salary": "50000",
            "dearness_allowance": "0",
            "hra_received": "5000",
            "other_allowances": "0",
        },
        "hra_inputs": {"rent_paid": "4000"},
        "other_income": "50000",
        "deductions_claimed": {
            "section_80c": "0",
            "section_80d": "0",
            "section_80ccd_1b": "0",
            "section_80e": "0",
            "section_24b": "0",
        },
        "age_bracket": "below_60",
        "city_type": "metro",
        "planning_eligibility": {
            "health_insurance_eligible": True,
            "eligible_health_insurance_premium": "500",
            "education_loan_eligible": True,
            "eligible_education_loan_interest": "500",
            "home_loan_eligible": True,
            "eligible_home_loan_interest": "500",
        },
    }
    values.update(overrides)
    return ConfirmedTaxpayerProfile.model_validate(values)


def _matching_test_rules():
    regime = regime_rules()
    return build_test_rules(old=regime, new=regime.model_copy(deep=True))


def test_each_suggestion_impact_matches_independent_engine_runs() -> None:
    confirmed = _confirmed_profile()
    rules = _matching_test_rules()
    profile = confirmed.to_taxpayer_profile()
    baseline = compare_regimes(profile, rules)
    drafts = build_suggestion_drafts(confirmed, rules)
    by_key = {draft.key: draft for draft in drafts}
    assert set(by_key) == {
        "80C_ELSS",
        "80C_PPF",
        "80D",
        "80CCD(1B)",
        "80E",
        "24B",
        "HRA",
    }

    sections = {
        "80C_ELSS": "80C",
        "80C_PPF": "80C",
        "80D": "80D",
        "80CCD(1B)": "80CCD(1B)",
        "80E": "80E",
        "24B": "24B",
        "HRA": None,
    }
    for key, draft in by_key.items():
        changed_profile = profile
        if sections[key] is not None:
            changed_profile = apply_simulation_change(
                profile,
                kind="deduction",
                section=sections[key],
                amount=draft.amount_to_invest,
            )
        expected_after = compare_regimes(changed_profile, rules)
        assert draft.before == baseline
        assert draft.after == expected_after
        expected_saved = max(
            Decimal("0"),
            min(baseline.old_regime.total_tax, baseline.new_regime.total_tax)
            - min(expected_after.old_regime.total_tax, expected_after.new_regime.total_tax),
        )
        assert draft.tax_saved == expected_saved
        assert draft.net_benefit == expected_saved


def test_alternative_80c_products_are_not_double_counted_in_summary() -> None:
    drafts = build_suggestion_drafts(_confirmed_profile(), _matching_test_rules())
    expected = sum(
        (
            max(draft.net_benefit for draft in drafts if draft.alternative_group == "80C"),
            *(draft.net_benefit for draft in drafts if draft.alternative_group is None),
        ),
        Decimal("0"),
    )
    assert savings_potential(drafts) == expected


def test_loan_and_health_suggestions_require_explicit_profile_eligibility() -> None:
    confirmed = _confirmed_profile(
        planning_eligibility={
            "health_insurance_eligible": False,
            "eligible_health_insurance_premium": "500",
            "education_loan_eligible": False,
            "eligible_education_loan_interest": "500",
            "home_loan_eligible": False,
            "eligible_home_loan_interest": "500",
        }
    )
    keys = {draft.key for draft in build_suggestion_drafts(confirmed, _matching_test_rules())}
    assert keys.isdisjoint({"80D", "80E", "24B"})


def test_simulation_returns_independent_before_after_comparison_and_delta() -> None:
    profile = TaxpayerProfile.model_validate(
        {
            "salary_components": {
                "basic_salary": "50000",
                "dearness_allowance": "0",
                "hra_received": "5000",
                "other_allowances": "0",
            },
            "hra_inputs": {"rent_paid": "4000"},
            "other_income": "50000",
            "age_bracket": "below_60",
            "city_type": "metro",
        }
    )
    rules = _matching_test_rules()
    changed = apply_simulation_change(
        profile,
        kind="deduction",
        section="80CCD(1B)",
        amount=Decimal("30"),
    )
    before = compare_regimes(profile, rules)
    after = compare_regimes(changed, rules)
    assert tax_difference(before, after) == (
        min(before.old_regime.total_tax, before.new_regime.total_tax)
        - min(after.old_regime.total_tax, after.new_regime.total_tax)
    )


def test_suggestion_terms_must_be_complete_and_verified() -> None:
    rules = _matching_test_rules()
    terms = rules.suggestion_terms["80C_ELSS"].model_copy(update={"status": "TODO"})
    rules = rules.model_copy(
        update={"suggestion_terms": {**rules.suggestion_terms, "80C_ELSS": terms}}
    )
    try:
        build_suggestion_drafts(_confirmed_profile(), rules)
    except ValueError as error:
        assert "80C_ELSS is not verified" in str(error)
    else:
        raise AssertionError("Unverified product terms must prevent generating suggestions.")
