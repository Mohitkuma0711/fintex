from decimal import Decimal
from typing import Literal

from app.schemas.tax import TaxpayerProfile, TaxResult, TraceStep
from app.services.tax_engine.rules import (
    DeductionRules,
    RegimeRules,
    RuleBoolean,
    RuleConfigurationError,
    RuleDecimal,
    RulesetVersion,
    SurchargeBand,
)
from app.services.tax_engine.trace import (
    boolean_rule,
    decimal_rule,
    make_trace_step,
)

ZERO = Decimal("0")
DEDUCTION_LABELS = {
    "80C": "section 80C",
    "80D": "section 80D",
    "80CCD(1B)": "section 80CCD(1B) NPS",
    "80E": "section 80E",
    "24B": "section 24B",
}


def _rule_path(regime: Literal["old", "new"], path: str) -> str:
    return f"regimes.{regime}.{path}"


def _referenced_rules(
    regime_rules: RegimeRules, path: str
) -> tuple[RuleDecimal | RuleBoolean, ...]:
    if path == "standard_deduction":
        return (regime_rules.standard_deduction,)
    if path == "hra":
        return (
            regime_rules.hra.enabled,
            regime_rules.hra.rent_less_percent,
            regime_rules.hra.metro_salary_percent,
            regime_rules.hra.non_metro_salary_percent,
        )
    if path.startswith("deductions."):
        section = path.removeprefix("deductions.")
        deduction = regime_rules.deductions[section]
        return (
            deduction.enabled,
            deduction.limit,
            *deduction.limits_by_age.values(),
        )
    if path.startswith("slabs["):
        index = int(path.removeprefix("slabs[").split("]", maxsplit=1)[0])
        slab = regime_rules.slabs[index]
        return (slab.lower_bound, slab.upper_bound, slab.rate)
    if path == "rebate":
        return (
            regime_rules.rebate.income_threshold,
            regime_rules.rebate.threshold_inclusive,
            regime_rules.rebate.maximum,
        )
    if path.startswith("surcharge_bands["):
        index = int(path.removeprefix("surcharge_bands[").split("]", maxsplit=1)[0])
        band = regime_rules.surcharge_bands[index]
        return (band.threshold, band.rate)
    if path == "cess_rate":
        return (regime_rules.cess_rate,)
    return ()


def _entry(
    rules: RulesetVersion,
    regime: Literal["old", "new"],
    *,
    label: str,
    formula: str,
    inputs: dict[str, Decimal | str | None],
    output: Decimal,
    path: str,
    why: str,
) -> TraceStep:
    return make_trace_step(
        label=label,
        formula=formula,
        inputs=inputs,
        output=output,
        act=rules.act,
        financial_year=rules.financial_year,
        regime=regime,
        rule_path=_rule_path(regime, path),
        plain_language_why=why,
        source_rules=_referenced_rules(rules.regimes[regime], path),
    )


def _deduction_limit(rule: DeductionRules, profile: TaxpayerProfile, path: str) -> Decimal:
    age_limit = rule.limits_by_age.get(profile.age_bracket)
    selected_rule = age_limit if age_limit is not None else rule.limit
    selected_path = f"{path}.limits_by_age.{profile.age_bracket}" if age_limit else f"{path}.limit"
    return decimal_rule(selected_rule, path=selected_path)


def _hra_exemption(
    profile: TaxpayerProfile,
    regime_rules: RegimeRules,
    rules: RulesetVersion,
    regime: Literal["old", "new"],
) -> tuple[Decimal, list[TraceStep]]:
    hra = regime_rules.hra
    enabled = boolean_rule(hra.enabled, path=_rule_path(regime, "hra.enabled"))
    rule_path = _rule_path(regime, "hra")
    salary_base = (
        profile.salary_components.basic_salary + profile.salary_components.dearness_allowance
    )
    if not enabled:
        exemption = ZERO
        formula = "0 because HRA exemption is not available in this regime"
        inputs = {"enabled": "false", "hra_received": profile.salary_components.hra_received}
        why = "This regime's verified rules do not allow an HRA exemption."
    else:
        rent_ratio = decimal_rule(hra.rent_less_percent, path=f"{rule_path}.rent_less_percent")
        salary_ratio_rule = (
            hra.metro_salary_percent
            if profile.city_type == "metro"
            else hra.non_metro_salary_percent
        )
        salary_ratio_name = (
            "metro_salary_percent" if profile.city_type == "metro" else "non_metro_salary_percent"
        )
        salary_ratio = decimal_rule(salary_ratio_rule, path=f"{rule_path}.{salary_ratio_name}")
        rent_less_amount = max(ZERO, profile.hra_inputs.rent_paid - salary_base * rent_ratio)
        salary_amount = salary_base * salary_ratio
        exemption = min(profile.salary_components.hra_received, rent_less_amount, salary_amount)
        formula = (
            "min(HRA received, max(0, rent paid - salary base × rent percentage), "
            "salary base × city percentage)"
        )
        inputs = {
            "enabled": "true",
            "hra_received": profile.salary_components.hra_received,
            "rent_paid": profile.hra_inputs.rent_paid,
            "salary_base": salary_base,
            "rent_less_percent": rent_ratio,
            "city_salary_percent": salary_ratio,
            "city_type": profile.city_type,
        }
        why = "The exempt amount is limited by the smallest of the verified HRA formula amounts."

    step = _entry(
        rules,
        regime,
        label="HRA exemption",
        formula=formula,
        inputs=inputs,
        output=exemption,
        path="hra",
        why=why,
    )
    return exemption, [step]


def _capped_deductions(
    profile: TaxpayerProfile,
    regime_rules: RegimeRules,
    rules: RulesetVersion,
    regime: Literal["old", "new"],
) -> tuple[dict[str, Decimal], list[TraceStep]]:
    claimed = profile.deductions_claimed.as_mapping()
    allowed: dict[str, Decimal] = {}
    steps: list[TraceStep] = []

    for section, deduction_rule in regime_rules.deductions.items():
        path = f"deductions.{section}"
        enabled = boolean_rule(deduction_rule.enabled, path=_rule_path(regime, f"{path}.enabled"))
        limit = _deduction_limit(deduction_rule, profile, _rule_path(regime, path))
        amount = min(claimed[section], limit) if enabled else ZERO
        allowed[section] = amount
        steps.append(
            _entry(
                rules,
                regime,
                label=f"{section} deduction",
                formula="min(amount claimed, applicable verified limit)"
                if enabled
                else "0 because deduction is unavailable in this regime",
                inputs={
                    "claimed": claimed[section],
                    "verified_limit": limit,
                    "enabled": "true" if enabled else "false",
                    "age_bracket": profile.age_bracket,
                },
                output=amount,
                path=path,
                why=(
                    f"The allowed {DEDUCTION_LABELS.get(section, section)} amount cannot exceed "
                    "the verified limit for this regime and age bracket."
                    if enabled
                    else (
                        f"Verified rules do not allow "
                        f"{DEDUCTION_LABELS.get(section, section)} in this regime."
                    )
                ),
            )
        )
    return allowed, steps


def _slab_tax(
    taxable_income: Decimal,
    regime_rules: RegimeRules,
    rules: RulesetVersion,
    regime: Literal["old", "new"],
) -> tuple[Decimal, list[TraceStep]]:
    tax = ZERO
    steps: list[TraceStep] = []
    for index, slab in enumerate(regime_rules.slabs):
        lower = decimal_rule(
            slab.lower_bound, path=_rule_path(regime, f"slabs[{index}].lower_bound")
        )
        upper = slab.upper_bound.value
        rate = decimal_rule(slab.rate, path=_rule_path(regime, f"slabs[{index}].rate"))
        if slab.upper_bound.status != "verified":
            raise RuleConfigurationError(
                f"Rule {_rule_path(regime, f'slabs[{index}].upper_bound')!r} is not verified"
            )
        if upper is None:
            if slab.upper_bound.source_url is None or slab.upper_bound.effective_from is None:
                raise RuleConfigurationError(
                    f"Open-ended rule {_rule_path(regime, f'slabs[{index}].upper_bound')!r} "
                    "requires source_url and effective_from"
                )
            taxable_in_slab = max(ZERO, taxable_income - lower)
        else:
            taxable_in_slab = max(ZERO, min(taxable_income, upper) - lower)
        slab_tax = taxable_in_slab * rate
        tax += slab_tax
        steps.append(
            _entry(
                rules,
                regime,
                label=f"Tax slab {index + 1}",
                formula="max(0, min(taxable income, upper bound) - lower bound) × rate"
                if upper is not None
                else "max(0, taxable income - lower bound) × rate",
                inputs={
                    "taxable_income": taxable_income,
                    "lower_bound": lower,
                    "upper_bound": upper,
                    "rate": rate,
                },
                output=slab_tax,
                path=f"slabs[{index}]",
                why="Only the income slice inside this verified slab is taxed at its rate.",
            )
        )
    return tax, steps


def _rebate(
    taxable_income: Decimal,
    tax: Decimal,
    regime_rules: RegimeRules,
    rules: RulesetVersion,
    regime: Literal["old", "new"],
) -> tuple[Decimal, TraceStep]:
    rebate_rules = regime_rules.rebate
    threshold = decimal_rule(
        rebate_rules.income_threshold,
        path=_rule_path(regime, "rebate.income_threshold"),
    )
    maximum = decimal_rule(rebate_rules.maximum, path=_rule_path(regime, "rebate.maximum"))
    inclusive = boolean_rule(
        rebate_rules.threshold_inclusive,
        path=_rule_path(regime, "rebate.threshold_inclusive"),
    )
    qualifies = taxable_income <= threshold if inclusive else taxable_income < threshold
    rebate = min(tax, maximum) if qualifies else ZERO
    step = _entry(
        rules,
        regime,
        label="Rebate",
        formula=(
            "min(slab tax, maximum rebate) when taxable income meets the "
            "verified threshold; otherwise 0"
        ),
        inputs={
            "taxable_income": taxable_income,
            "income_threshold": threshold,
            "threshold_inclusive": "true" if inclusive else "false",
            "maximum_rebate": maximum,
            "slab_tax": tax,
        },
        output=rebate,
        path="rebate",
        why=(
            "A rebate applies only when taxable income meets the verified "
            "regime threshold, capped at its verified maximum."
        ),
    )
    return rebate, step


def _selected_surcharge_band(
    taxable_income: Decimal, bands: list[SurchargeBand], regime: Literal["old", "new"]
) -> tuple[SurchargeBand | None, int | None]:
    selected: SurchargeBand | None = None
    selected_index: int | None = None
    for index, band in enumerate(bands):
        if band.threshold.value is None:
            raise RuleConfigurationError(
                f"Rule regimes.{regime}.surcharge_bands[{index}].threshold has no value"
            )
        if taxable_income >= band.threshold.value:
            selected = band
            selected_index = index
    return selected, selected_index


def _surcharge(
    taxable_income: Decimal,
    tax_after_rebate: Decimal,
    bands: list[SurchargeBand],
    rules: RulesetVersion,
    regime: Literal["old", "new"],
) -> tuple[Decimal, TraceStep]:
    selected, selected_index = _selected_surcharge_band(taxable_income, bands, regime)
    if selected is None or selected_index is None:
        rate = ZERO
        threshold: Decimal | None = None
        path = "surcharge_bands"
        why = "Taxable income does not meet any verified surcharge threshold."
    else:
        rate = decimal_rule(
            selected.rate,
            path=_rule_path(regime, f"surcharge_bands[{selected_index}].rate"),
        )
        threshold = decimal_rule(
            selected.threshold,
            path=_rule_path(regime, f"surcharge_bands[{selected_index}].threshold"),
        )
        path = f"surcharge_bands[{selected_index}]"
        why = "The applicable verified surcharge rate is applied to tax remaining after rebate."
    surcharge = tax_after_rebate * rate
    step = _entry(
        rules,
        regime,
        label="Surcharge",
        formula="tax after rebate × applicable surcharge rate",
        inputs={
            "tax_after_rebate": tax_after_rebate,
            "taxable_income": taxable_income,
            "threshold": threshold,
            "rate": rate,
        },
        output=surcharge,
        path=path,
        why=why,
    )
    return surcharge, step


def calculate_regime(
    profile: TaxpayerProfile,
    rules: RulesetVersion,
    regime: Literal["old", "new"],
) -> TaxResult:
    rules.require_ready(regime)
    regime_rules = rules.regimes[regime]
    trace: list[TraceStep] = []
    gross_income = profile.salary_components.total + profile.other_income
    trace.append(
        _entry(
            rules,
            regime,
            label="Gross income",
            formula=("basic salary + dearness allowance + HRA + other allowances + other income"),
            inputs={
                "basic_salary": profile.salary_components.basic_salary,
                "dearness_allowance": profile.salary_components.dearness_allowance,
                "hra_received": profile.salary_components.hra_received,
                "other_allowances": profile.salary_components.other_allowances,
                "other_income": profile.other_income,
            },
            output=gross_income,
            path="tax_engine.gross_income",
            why="Gross income combines the supplied salary components and other income.",
        )
    )

    standard_deduction_limit = decimal_rule(
        regime_rules.standard_deduction,
        path=_rule_path(regime, "standard_deduction"),
    )
    salary_income = profile.salary_components.total
    standard_deduction = min(salary_income, standard_deduction_limit)
    trace.append(
        _entry(
            rules,
            regime,
            label="Standard deduction",
            formula="min(salary income, verified standard deduction)",
            inputs={
                "salary_income": salary_income,
                "verified_limit": standard_deduction_limit,
            },
            output=standard_deduction,
            path="standard_deduction",
            why="The deduction is limited to the salary income and the verified ruleset amount.",
        )
    )

    hra_exemption, hra_steps = _hra_exemption(profile, regime_rules, rules, regime)
    trace.extend(hra_steps)
    deductions, deduction_steps = _capped_deductions(profile, regime_rules, rules, regime)
    trace.extend(deduction_steps)
    total_deductions = sum(deductions.values(), ZERO)
    taxable_income = max(ZERO, gross_income - standard_deduction - hra_exemption - total_deductions)
    trace.append(
        _entry(
            rules,
            regime,
            label="Taxable income",
            formula=(
                "max(0, gross income - standard deduction - HRA exemption "
                "- Chapter VI-A deductions)"
            ),
            inputs={
                "gross_income": gross_income,
                "standard_deduction": standard_deduction,
                "hra_exemption": hra_exemption,
                "chapter_vi_a_deductions": total_deductions,
            },
            output=taxable_income,
            path="tax_engine.taxable_income",
            why="Taxable income follows deductions and cannot be below zero.",
        )
    )

    tax_before_rebate, slab_steps = _slab_tax(taxable_income, regime_rules, rules, regime)
    trace.extend(slab_steps)
    trace.append(
        _entry(
            rules,
            regime,
            label="Tax before rebate",
            formula="sum of tax calculated across each progressive slab",
            inputs={"taxable_income": taxable_income},
            output=tax_before_rebate,
            path="tax_engine.slab_tax",
            why="This sums the traced tax slices across verified slabs.",
        )
    )
    rebate, rebate_step = _rebate(taxable_income, tax_before_rebate, regime_rules, rules, regime)
    trace.append(rebate_step)
    tax_after_rebate = max(ZERO, tax_before_rebate - rebate)
    surcharge, surcharge_step = _surcharge(
        taxable_income,
        tax_after_rebate,
        regime_rules.surcharge_bands,
        rules,
        regime,
    )
    trace.append(surcharge_step)
    cess_rate = decimal_rule(regime_rules.cess_rate, path=_rule_path(regime, "cess_rate"))
    cess_base = tax_after_rebate + surcharge
    cess = cess_base * cess_rate
    trace.append(
        _entry(
            rules,
            regime,
            label="Cess",
            formula="(tax after rebate + surcharge) × verified cess rate",
            inputs={
                "tax_after_rebate": tax_after_rebate,
                "surcharge": surcharge,
                "cess_rate": cess_rate,
            },
            output=cess,
            path="cess_rate",
            why="Cess is applied to the post-rebate tax and surcharge using the verified rate.",
        )
    )
    total_tax = tax_after_rebate + surcharge + cess
    trace.append(
        _entry(
            rules,
            regime,
            label="Total tax",
            formula="tax before rebate - rebate + surcharge + cess",
            inputs={
                "tax_before_rebate": tax_before_rebate,
                "rebate": rebate,
                "surcharge": surcharge,
                "cess": cess,
            },
            output=total_tax,
            path="tax_engine.total_tax",
            why="The final amount adds surcharge and cess after subtracting the applicable rebate.",
        )
    )

    return TaxResult(
        regime=regime,
        act=rules.act,
        financial_year=rules.financial_year,
        rules_version=rules.version,
        gross_income=gross_income,
        standard_deduction=standard_deduction,
        hra_exemption=hra_exemption,
        deductions=deductions,
        taxable_income=taxable_income,
        tax_before_rebate=tax_before_rebate,
        rebate=rebate,
        surcharge=surcharge,
        cess=cess,
        total_tax=total_tax,
        trace=trace,
    )
