"""Deterministic, versioned-rule-driven income-tax calculations."""

from app.schemas.tax import (
    DeductionsClaimed,
    HRAInputs,
    SalaryComponents,
    TaxComparisonResult,
    TaxpayerProfile,
    TaxResult,
    TraceStep,
)
from app.services.tax_engine.compare import compare_regimes
from app.services.tax_engine.new_regime import calculate_new_regime
from app.services.tax_engine.old_regime import calculate_old_regime
from app.services.tax_engine.rules import (
    RuleConfigurationError,
    RulesetVersion,
    load_rules,
)

__all__ = [
    "DeductionsClaimed",
    "HRAInputs",
    "RuleConfigurationError",
    "RulesetVersion",
    "SalaryComponents",
    "TaxComparisonResult",
    "TaxResult",
    "TaxpayerProfile",
    "TraceStep",
    "calculate_new_regime",
    "calculate_old_regime",
    "compare_regimes",
    "load_rules",
]
