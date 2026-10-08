from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.tax import DeductionsClaimed, HRAInputs, SalaryComponents, TaxpayerProfile
from app.services.tax_engine import (
    RuleConfigurationError,
    calculate_new_regime,
    calculate_old_regime,
    compare_regimes,
    load_rules,
)
from app.services.tax_engine.common import (
    _capped_deductions,
    _rebate,
    _selected_surcharge_band,
    _slab_tax,
    _surcharge,
)
from app.services.tax_engine.rules import (
    RuleDecimal,
    RulesDocument,
    RulesetVersion,
)
from app.services.tax_engine.rules import (
    load_rules as load_rules_from_path,
)
from app.services.tax_engine.trace import boolean_rule, decimal_rule, make_trace_step
from tests.unit.tax_engine_fixtures import (
    build_test_rules,
    flag,
    number,
    regime_rules,
    taxpayer_profile,
)

ZERO = Decimal("0")


def test_profile_defaults_and_decimal_string_inputs() -> None:
    profile = taxpayer_profile(
        salary_components={"basic_salary": "1000.25"},
        other_income="5.75",
    )

    assert profile.salary_components.total == Decimal("1000.25")
    assert profile.hra_inputs.rent_paid == ZERO
    assert profile.deductions_claimed.section_80c == ZERO
    assert profile.other_income == Decimal("5.75")
    assert profile.deductions_claimed.as_mapping()["80CCD(1B)"] == ZERO


@pytest.mark.parametrize(
    "model, data",
    [
        (SalaryComponents, {"basic_salary": -1}),
        (HRAInputs, {"rent_paid": "-1"}),
        (DeductionsClaimed, {"section_80c": "-1"}),
        (TaxpayerProfile, {"age_bracket": "minor", "city_type": "metro"}),
        (TaxpayerProfile, {"age_bracket": "below_60", "city_type": "small_town"}),
        (SalaryComponents, {"basic_salary": 1.25}),
    ],
)
def test_profile_rejects_invalid_or_binary_float_values(model, data) -> None:
    with pytest.raises(ValidationError):
        model.model_validate(data)


def test_unverified_production_rules_are_loadable_but_not_executable() -> None:
    rules = load_rules("TODO: assign financial year")

    assert rules.version == "TODO: assign ruleset version"
    assert rules.act == "Income-tax Act, 2025"
    with pytest.raises(RuleConfigurationError, match="not verified"):
        calculate_old_regime(taxpayer_profile(), rules)


def test_zero_income_returns_zero_tax_and_a_complete_trace() -> None:
    result = calculate_old_regime(taxpayer_profile(), build_test_rules())

    assert result.gross_income == ZERO
    assert result.taxable_income == ZERO
    assert result.total_tax == ZERO
    assert result.trace[0].label == "Gross income"
    assert result.trace[-1].label == "Total tax"
    assert all(step.rule_reference and step.plain_language_why for step in result.trace)


def test_salary_standard_deduction_and_hra_use_verified_rules() -> None:
    profile = taxpayer_profile(
        salary_components={
            "basic_salary": "10000",
            "dearness_allowance": "1000",
            "hra_received": "6000",
        },
        hra_inputs={"rent_paid": "9000"},
        city_type="metro",
    )
    result = calculate_old_regime(profile, build_test_rules())

    assert result.gross_income == Decimal("17000")
    assert result.standard_deduction == Decimal("1000")
    assert result.hra_exemption == Decimal("3500")
    hra_step = next(step for step in result.trace if step.label == "HRA exemption")
    assert hra_step.inputs["salary_base"] == Decimal("11000")
    assert "regimes.old.hra" in hra_step.rule_reference
    assert "incometax.gov.in" in hra_step.rule_reference


def test_hra_non_metro_uses_city_percentage_and_nonnegative_rent_amount() -> None:
    rules = build_test_rules()
    profile = taxpayer_profile(
        salary_components={
            "basic_salary": "10000",
            "hra_received": "5000",
        },
        hra_inputs={"rent_paid": "100"},
        city_type="non_metro",
    )
    result = calculate_old_regime(profile, rules)

    assert result.hra_exemption == ZERO
    assert next(step for step in result.trace if step.label == "HRA exemption").inputs[
        "city_salary_percent"
    ] == Decimal("0.4")


def test_hra_disabled_in_rules_produces_zero_exemption() -> None:
    rules = build_test_rules(new=regime_rules(hra_enabled=False))
    profile = taxpayer_profile(
        salary_components={"basic_salary": "1000", "hra_received": "800"},
        hra_inputs={"rent_paid": "600"},
    )

    result = calculate_new_regime(profile, rules)

    assert result.hra_exemption == ZERO
    step = next(step for step in result.trace if step.label == "HRA exemption")
    assert step.inputs["enabled"] == "false"


def test_deductions_are_capped_by_rule_and_age_specific_limit() -> None:
    rules = build_test_rules()
    profile = taxpayer_profile(
        age_bracket="60_to_79",
        deductions_claimed={
            "section_80c": "150",
            "section_80d": "150",
            "section_80ccd_1b": "50",
            "section_80e": "25",
            "section_24b": "50",
        },
    )
    result = calculate_old_regime(profile, rules)

    assert result.deductions == {
        "80C": Decimal("100"),
        "80D": Decimal("70"),
        "80CCD(1B)": Decimal("30"),
        "80E": Decimal("20"),
        "24B": Decimal("40"),
    }
    section_80d = next(step for step in result.trace if step.label == "80D deduction")
    assert section_80d.inputs["age_bracket"] == "60_to_79"
    assert section_80d.inputs["verified_limit"] == Decimal("70")


def test_disabled_deductions_are_zero_and_use_configured_limits() -> None:
    rules = build_test_rules(old=regime_rules(deductions_enabled=False))
    profile = taxpayer_profile(deductions_claimed={"section_80c": "99"})
    amounts, steps = _capped_deductions(profile, rules.regimes["old"], rules, "old")

    assert amounts["80C"] == ZERO
    assert len(steps) == 5
    assert next(step for step in steps if step.label == "80C deduction").inputs[
        "verified_limit"
    ] == Decimal("100")


def test_deduction_age_without_override_uses_general_limit() -> None:
    rules = build_test_rules(old=regime_rules(section_80d_age_limits={"below_60": "50"}))
    profile = taxpayer_profile(age_bracket="80_plus")
    amounts, _steps = _capped_deductions(profile, rules.regimes["old"], rules, "old")
    assert amounts["80D"] == ZERO


def test_taxable_income_floors_at_zero() -> None:
    rules = build_test_rules(old=regime_rules(standard_deduction="1000", hra_enabled=False))
    profile = taxpayer_profile(
        salary_components={"basic_salary": "100"},
        deductions_claimed={"section_80c": "100"},
    )
    result = calculate_old_regime(profile, rules)

    assert result.taxable_income == ZERO
    assert result.total_tax == ZERO


def test_progressive_slabs_tax_only_income_inside_each_band() -> None:
    rules = build_test_rules()
    tax, steps = _slab_tax(Decimal("6000"), rules.regimes["old"], rules, "old")

    assert tax == Decimal("600")
    assert [step.output for step in steps] == [
        ZERO,
        Decimal("400"),
        Decimal("200"),
    ]


def test_rebate_is_inclusive_at_boundary_and_capped_by_tax() -> None:
    rules = build_test_rules()
    rebate, _step = _rebate(Decimal("2000"), Decimal("50"), rules.regimes["old"], rules, "old")

    assert rebate == Decimal("50")


def test_rebate_exclusive_boundary_and_rebate_above_maximum() -> None:
    rules = build_test_rules(old=regime_rules(rebate_inclusive=False, rebate_maximum="40"))
    regime = rules.regimes["old"]
    at_boundary, _step = _rebate(Decimal("2000"), Decimal("100"), regime, rules, "old")
    below_boundary, _step = _rebate(Decimal("1999"), Decimal("100"), regime, rules, "old")

    assert at_boundary == ZERO
    assert below_boundary == Decimal("40")


def test_rebate_does_not_apply_above_threshold() -> None:
    rules = build_test_rules()
    rebate, _step = _rebate(Decimal("2001"), Decimal("100"), rules.regimes["old"], rules, "old")
    assert rebate == ZERO


def test_surcharge_selects_highest_qualifying_band_and_zero_if_none() -> None:
    rules = build_test_rules()
    bands = rules.regimes["old"].surcharge_bands
    selected, index = _selected_surcharge_band(Decimal("10000"), bands, "old")
    no_band, no_index = _selected_surcharge_band(Decimal("0"), bands, "old")
    surcharge, _step = _surcharge(Decimal("10000"), Decimal("100"), bands, rules, "old")

    assert selected is bands[1] and index == 1
    assert no_band is bands[0] and no_index == 0
    assert surcharge == Decimal("10")


def test_surcharge_handles_no_qualifying_threshold() -> None:
    rules = build_test_rules(old=regime_rules(surcharge_bands=[("1", "0.1")]))
    surcharge, step = _surcharge(
        ZERO, Decimal("100"), rules.regimes["old"].surcharge_bands, rules, "old"
    )
    assert surcharge == ZERO
    assert step.inputs["rate"] == ZERO
    assert step.rule_reference.endswith("surcharge_bands")


def test_regime_comparison_returns_exact_saving_and_prefers_old_on_tie() -> None:
    profile = taxpayer_profile(
        salary_components={"basic_salary": "8000"},
    )
    result = compare_regimes(profile, build_test_rules())

    assert result.recommended_regime == "new"
    assert result.saving == result.old_regime.total_tax - result.new_regime.total_tax
    tie_rules = build_test_rules(
        old=regime_rules(
            standard_deduction="0",
            hra_enabled=False,
            deductions_enabled=False,
            slabs=[("0", None, "0")],
            rebate_threshold="0",
            rebate_maximum="0",
            surcharge_bands=[("0", "0")],
            cess_rate="0",
        ),
        new=regime_rules(
            standard_deduction="0",
            hra_enabled=False,
            deductions_enabled=False,
            slabs=[("0", None, "0")],
            rebate_threshold="0",
            rebate_maximum="0",
            surcharge_bands=[("0", "0")],
            cess_rate="0",
        ),
    )
    tie = compare_regimes(profile, tie_rules)
    assert tie.recommended_regime == "old"
    assert tie.saving == ZERO


@pytest.mark.parametrize(
    "rule, path, expected",
    [
        (number("7"), "sample.numeric", Decimal("7")),
        (flag(True), "sample.boolean", True),
    ],
)
def test_trace_rule_value_helpers_accept_verified_values(rule, path, expected) -> None:
    actual = (
        decimal_rule(rule, path=path)
        if isinstance(rule, type(number("0")))
        else boolean_rule(rule, path=path)
    )
    assert actual == expected


@pytest.mark.parametrize(
    "rule, helper",
    [
        (
            number("1").model_copy(update={"status": "TODO"}),
            decimal_rule,
        ),
        (number(None), decimal_rule),
        (
            flag(True).model_copy(update={"status": "TODO"}),
            boolean_rule,
        ),
        (flag(None), boolean_rule),
    ],
)
def test_trace_rule_value_helpers_reject_incomplete_entries(rule, helper) -> None:
    with pytest.raises(RuleConfigurationError):
        helper(rule, path="sample.rule")


def test_trace_step_contains_auditable_reference_and_explanation() -> None:
    step = make_trace_step(
        label="Example",
        formula="a + b",
        inputs={"a": Decimal("1"), "b": Decimal("2")},
        output=Decimal("3"),
        act="Test Act",
        financial_year="FY test",
        regime="old",
        rule_path="sample",
        plain_language_why="The example adds two values.",
    )

    assert step.output == Decimal("3")
    assert step.rule_reference == "Test Act / FY FY test / old / sample"
    assert step.plain_language_why


def test_ruleset_rejects_rates_above_one() -> None:
    rules = build_test_rules(old=regime_rules(cess_rate="1.01"))
    with pytest.raises(RuleConfigurationError, match="greater than 1"):
        rules.require_ready("old")


def test_ruleset_rejects_noncontiguous_slabs() -> None:
    rules = build_test_rules(old=regime_rules(slabs=[("0", "100", "0"), ("101", None, "0.1")]))
    with pytest.raises(RuleConfigurationError, match="not contiguous"):
        rules.require_ready("old")


def test_ruleset_rejects_bad_or_nonfinal_open_slabs() -> None:
    nonzero_start = build_test_rules(old=regime_rules(slabs=[("1", None, "0")]))
    with pytest.raises(RuleConfigurationError, match="first slab must start at zero"):
        nonzero_start.require_ready("old")
    bad_width = build_test_rules(old=regime_rules(slabs=[("0", "0", "0")]))
    with pytest.raises(RuleConfigurationError, match="must exceed"):
        bad_width.require_ready("old")
    open_before_last = build_test_rules(
        old=regime_rules(slabs=[("0", None, "0"), ("1", None, "0")])
    )
    with pytest.raises(RuleConfigurationError, match="only the final slab"):
        open_before_last.require_ready("old")
    finite_final = build_test_rules(old=regime_rules(slabs=[("0", "100", "0")]))
    with pytest.raises(RuleConfigurationError, match="final slab must have"):
        finite_final.require_ready("old")


def test_ruleset_requires_official_source_and_effective_date() -> None:
    rules = build_test_rules()
    rules.regimes["old"].cess_rate = RuleDecimal(
        value=Decimal("0.04"),
        status="verified",
        source_url="https://example.org/tax",
        effective_from=date(2025, 4, 1),
    )
    with pytest.raises(RuleConfigurationError, match="not on an official tax domain"):
        rules.require_ready("old")

    rules = build_test_rules()
    rules.regimes["old"].cess_rate.effective_from = None
    with pytest.raises(RuleConfigurationError, match="no effective_from"):
        rules.require_ready("old")


def test_ruleset_requires_metadata_for_open_ended_final_slab() -> None:
    rules = build_test_rules()
    rules.regimes["old"].slabs[-1].upper_bound.source_url = None
    with pytest.raises(RuleConfigurationError, match="no source_url"):
        rules.require_ready("old")


def test_ruleset_rejects_empty_surcharge_bands() -> None:
    rules = build_test_rules()
    rules.regimes["old"].surcharge_bands = []
    with pytest.raises(RuleConfigurationError, match="at least one surcharge band"):
        rules.require_ready("old")


def test_ruleset_requires_open_surcharge_threshold_and_sorted_bands() -> None:
    rules = build_test_rules()
    rules.regimes["old"].surcharge_bands[0].threshold.value = None
    with pytest.raises(RuleConfigurationError, match="no verified value"):
        rules.require_ready("old")
    with pytest.raises(RuleConfigurationError, match="has no value"):
        _selected_surcharge_band(Decimal("10"), rules.regimes["old"].surcharge_bands, "old")

    rules = build_test_rules(old=regime_rules(surcharge_bands=[("10", "0.1"), ("0", "0")]))
    with pytest.raises(RuleConfigurationError, match="unique and sorted"):
        rules.require_ready("old")

    duplicate_thresholds = build_test_rules(
        old=regime_rules(surcharge_bands=[("0", "0"), ("0", "0.1")])
    )
    with pytest.raises(RuleConfigurationError, match="unique and sorted"):
        duplicate_thresholds.require_ready("old")


def test_surcharge_refuses_unverified_selected_rate() -> None:
    rules = build_test_rules()
    rules.regimes["old"].surcharge_bands[0].rate.status = "TODO"
    with pytest.raises(RuleConfigurationError, match="not verified"):
        rules.require_ready("old")


def test_loader_reports_unknown_act_financial_year_and_duplicate_versions(tmp_path) -> None:
    with pytest.raises(RuleConfigurationError, match="not requested Act"):
        load_rules("TODO: assign financial year", act="Other Act")
    with pytest.raises(RuleConfigurationError, match="No rules"):
        load_rules("FY missing")

    rules_path = tmp_path / "rules.json"
    document = {
        "schema_version": 1,
        "act": "Synthetic Act",
        "versions": [
            {
                "version": "one",
                "financial_year": "FY test",
                "effective_from": None,
                "regimes": {
                    "old": regime_rules().model_dump(mode="json"),
                    "new": regime_rules().model_dump(mode="json"),
                },
            },
            {
                "version": "two",
                "financial_year": "FY test",
                "effective_from": None,
                "regimes": {
                    "old": regime_rules().model_dump(mode="json"),
                    "new": regime_rules().model_dump(mode="json"),
                },
            },
        ],
    }
    import json

    rules_path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(RuleConfigurationError, match="Multiple versions"):
        load_rules_from_path("FY test", act="Synthetic Act", path=rules_path)


@pytest.mark.parametrize(
    "raw",
    [
        "{malformed",
        "[]",
        '{"schema_version": 7, "act": "x", "versions": []}',
    ],
)
def test_loader_rejects_invalid_documents(tmp_path, raw) -> None:
    path = tmp_path / "invalid.json"
    path.write_text(raw, encoding="utf-8")
    with pytest.raises(RuleConfigurationError, match="Unable to load valid rules"):
        load_rules_from_path("FY", path=path)


def test_loader_reports_missing_file(tmp_path) -> None:
    with pytest.raises(RuleConfigurationError, match="Unable to load valid rules"):
        load_rules_from_path("FY", path=tmp_path / "missing.json")


def test_rules_models_reject_float_rule_parameters_and_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        RuleDecimal(
            value=1.25,
            status="verified",
            source_url="https://www.incometax.gov.in/",
            effective_from=date(2025, 4, 1),
        )
    with pytest.raises(ValidationError):
        RulesetVersion(
            act="Act",
            version="v1",
            financial_year="FY",
            effective_from=None,
            regimes={"old": regime_rules(), "new": regime_rules(), "other": regime_rules()},
        )
    with pytest.raises(ValidationError):
        RulesDocument.model_validate(
            {"schema_version": 1, "act": "Act", "versions": [], "unexpected": True}
        )
