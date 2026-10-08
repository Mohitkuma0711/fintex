from app.schemas.tax import TaxpayerProfile, TaxResult
from app.services.tax_engine.common import calculate_regime
from app.services.tax_engine.rules import RulesetVersion


def calculate_new_regime(profile: TaxpayerProfile, rules: RulesetVersion) -> TaxResult:
    """Calculate under new-regime parameters from a verified, selected ruleset."""
    return calculate_regime(profile, rules, "new")
