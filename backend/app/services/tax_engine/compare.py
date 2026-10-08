from app.schemas.tax import TaxComparisonResult, TaxpayerProfile
from app.services.tax_engine.new_regime import calculate_new_regime
from app.services.tax_engine.old_regime import calculate_old_regime
from app.services.tax_engine.rules import RulesetVersion


def compare_regimes(profile: TaxpayerProfile, rules: RulesetVersion) -> TaxComparisonResult:
    old_result = calculate_old_regime(profile, rules)
    new_result = calculate_new_regime(profile, rules)
    if old_result.total_tax <= new_result.total_tax:
        recommended = "old"
        saving = new_result.total_tax - old_result.total_tax
    else:
        recommended = "new"
        saving = old_result.total_tax - new_result.total_tax
    return TaxComparisonResult(
        old_regime=old_result,
        new_regime=new_result,
        recommended_regime=recommended,
        saving=saving,
    )
