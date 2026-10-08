from decimal import Decimal
from typing import Literal

from app.schemas.tax import TraceStep
from app.services.tax_engine.rules import RuleBoolean, RuleConfigurationError, RuleDecimal


def decimal_rule(rule: RuleDecimal, *, path: str) -> Decimal:
    if rule.status != "verified" or rule.value is None:
        raise RuleConfigurationError(f"Rule {path!r} has no verified numeric value")
    return rule.value


def boolean_rule(rule: RuleBoolean, *, path: str) -> bool:
    if rule.status != "verified" or rule.value is None:
        raise RuleConfigurationError(f"Rule {path!r} has no verified boolean value")
    return rule.value


def make_trace_step(
    *,
    label: str,
    formula: str,
    inputs: dict[str, Decimal | str | None],
    output: Decimal,
    act: str,
    financial_year: str,
    regime: Literal["old", "new"],
    rule_path: str,
    plain_language_why: str,
    source_rules: tuple[RuleDecimal | RuleBoolean, ...] = (),
) -> TraceStep:
    source_references = tuple(
        f"{rule.source_url} (effective from {rule.effective_from})"
        for rule in source_rules
        if rule.source_url is not None and rule.effective_from is not None
    )
    reference = f"{act} / FY {financial_year} / {regime} / {rule_path}"
    if source_references:
        reference = f"{reference} / sources: {'; '.join(source_references)}"

    return TraceStep(
        label=label,
        formula=formula,
        inputs=inputs,
        output=output,
        rule_reference=reference,
        plain_language_why=plain_language_why,
    )
