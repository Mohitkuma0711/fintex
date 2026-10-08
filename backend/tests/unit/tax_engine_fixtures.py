from datetime import date
from decimal import Decimal

from app.schemas.tax import TaxpayerProfile
from app.services.tax_engine.rules import (
    DeductionRules,
    HraRules,
    RebateRules,
    RegimeRules,
    RuleBoolean,
    RuleDecimal,
    RulesetVersion,
    SuggestionTerms,
    SurchargeBand,
    TaxSlab,
)

SOURCE_URL = "https://www.incometax.gov.in/iec/foportal/"
EFFECTIVE_FROM = date(2025, 4, 1)


def number(value: str | None) -> RuleDecimal:
    return RuleDecimal(
        value=Decimal(value) if value is not None else None,
        status="verified",
        source_url=SOURCE_URL,
        effective_from=EFFECTIVE_FROM,
    )


def flag(value: bool) -> RuleBoolean:
    return RuleBoolean(
        value=value,
        status="verified",
        source_url=SOURCE_URL,
        effective_from=EFFECTIVE_FROM,
    )


def deduction_rules(
    limit: str, *, enabled: bool = True, age_limits: dict[str, str] | None = None
) -> DeductionRules:
    return DeductionRules(
        enabled=flag(enabled),
        limit=number(limit),
        limits_by_age={key: number(value) for key, value in (age_limits or {}).items()},
    )


def regime_rules(
    *,
    standard_deduction: str = "1000",
    hra_enabled: bool = True,
    hra_rent_percentage: str = "0.5",
    hra_metro_percentage: str = "0.5",
    hra_non_metro_percentage: str = "0.4",
    deductions_enabled: bool = True,
    section_80d_age_limits: dict[str, str] | None = None,
    slabs: list[tuple[str, str | None, str]] | None = None,
    rebate_threshold: str = "2000",
    rebate_inclusive: bool = True,
    rebate_maximum: str = "100",
    surcharge_bands: list[tuple[str, str]] | None = None,
    cess_rate: str = "0.04",
) -> RegimeRules:
    slab_data = slabs or [
        ("0", "1000", "0"),
        ("1000", "5000", "0.1"),
        ("5000", None, "0.2"),
    ]
    surcharge_data = surcharge_bands or [("0", "0"), ("10000", "0.1")]
    return RegimeRules(
        standard_deduction=number(standard_deduction),
        hra=HraRules(
            enabled=flag(hra_enabled),
            rent_less_percent=number(hra_rent_percentage),
            metro_salary_percent=number(hra_metro_percentage),
            non_metro_salary_percent=number(hra_non_metro_percentage),
        ),
        deductions={
            "80C": deduction_rules("100", enabled=deductions_enabled),
            "80D": deduction_rules(
                "50",
                enabled=deductions_enabled,
                age_limits=section_80d_age_limits
                or {"below_60": "50", "60_to_79": "70", "80_plus": "90"},
            ),
            "80CCD(1B)": deduction_rules("30", enabled=deductions_enabled),
            "80E": deduction_rules("20", enabled=deductions_enabled),
            "24B": deduction_rules("40", enabled=deductions_enabled),
        },
        slabs=[
            TaxSlab(
                lower_bound=number(lower),
                upper_bound=number(upper),
                rate=number(rate),
            )
            for lower, upper, rate in slab_data
        ],
        rebate=RebateRules(
            income_threshold=number(rebate_threshold),
            threshold_inclusive=flag(rebate_inclusive),
            maximum=number(rebate_maximum),
        ),
        surcharge_bands=[
            SurchargeBand(threshold=number(threshold), rate=number(rate))
            for threshold, rate in surcharge_data
        ],
        cess_rate=number(cess_rate),
    )


def build_test_rules(
    *,
    old: RegimeRules | None = None,
    new: RegimeRules | None = None,
    version: str = "test-only-1",
) -> RulesetVersion:
    return RulesetVersion(
        act="Synthetic test-only Act",
        version=version,
        financial_year="Synthetic FY",
        effective_from=EFFECTIVE_FROM,
        suggestion_terms={
            key: SuggestionTerms(
                title=title,
                lock_in_period="No fixed lock-in in this synthetic test fixture.",
                liquidity_note="Synthetic test-only liquidity description.",
                status="verified",
                source_url=SOURCE_URL,
                effective_from=EFFECTIVE_FROM,
            )
            for key, title in {
                "80C_ELSS": "Synthetic ELSS",
                "80C_PPF": "Synthetic PPF",
                "80D": "Synthetic health cover",
                "80CCD(1B)": "Synthetic NPS",
                "80E": "Synthetic education loan",
                "24B": "Synthetic home loan",
                "HRA": "Synthetic rent evidence",
            }.items()
        },
        regimes={
            "old": old or regime_rules(),
            "new": new
            or regime_rules(
                standard_deduction="2000",
                hra_enabled=False,
                deductions_enabled=False,
                slabs=[("0", "2000", "0"), ("2000", None, "0.15")],
                rebate_threshold="1500",
                rebate_maximum="50",
                surcharge_bands=[("0", "0")],
                cess_rate="0.03",
            ),
        },
    )


def taxpayer_profile(**overrides: object) -> TaxpayerProfile:
    profile: dict[str, object] = {
        "age_bracket": "below_60",
        "city_type": "metro",
    }
    profile.update(overrides)
    return TaxpayerProfile.model_validate(profile)
