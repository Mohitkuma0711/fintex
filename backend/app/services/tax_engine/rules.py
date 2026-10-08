import json
from datetime import date
from decimal import Decimal
from numbers import Real
from pathlib import Path
from typing import Annotated, Literal

from pydantic import (
    AnyHttpUrl,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
)

from app.schemas.tax import AgeBracket

RULES_FILE = Path(__file__).resolve().parents[2] / "rules" / "income_tax_act_2025.json"
OFFICIAL_SOURCE_HOSTS = {"incometax.gov.in", "incometaxindia.gov.in"}


class RuleConfigurationError(ValueError):
    """Raised when a ruleset is invalid, missing, or not ready for calculations."""


def _reject_json_number(value: object) -> object:
    if isinstance(value, Real):
        raise ValueError("Rule values must be JSON decimal strings")
    return value


RuleNumber = Annotated[
    Decimal,
    BeforeValidator(_reject_json_number),
    Field(ge=Decimal("0"), max_digits=24, decimal_places=8),
]


class RuleModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RuleDecimal(RuleModel):
    value: RuleNumber | None
    status: Literal["TODO", "verified"]
    source_url: AnyHttpUrl | None
    effective_from: date | None


class RuleBoolean(RuleModel):
    value: bool | None
    status: Literal["TODO", "verified"]
    source_url: AnyHttpUrl | None
    effective_from: date | None


class HraRules(RuleModel):
    enabled: RuleBoolean
    rent_less_percent: RuleDecimal
    metro_salary_percent: RuleDecimal
    non_metro_salary_percent: RuleDecimal


class DeductionRules(RuleModel):
    enabled: RuleBoolean
    limit: RuleDecimal
    limits_by_age: dict[AgeBracket, RuleDecimal] = Field(default_factory=dict)


class TaxSlab(RuleModel):
    lower_bound: RuleDecimal
    upper_bound: RuleDecimal
    rate: RuleDecimal


class RebateRules(RuleModel):
    income_threshold: RuleDecimal
    threshold_inclusive: RuleBoolean
    maximum: RuleDecimal


class SurchargeBand(RuleModel):
    threshold: RuleDecimal
    rate: RuleDecimal


class SuggestionTerms(RuleModel):
    title: str = Field(min_length=1)
    lock_in_period: str | None
    liquidity_note: str | None
    status: Literal["TODO", "verified"]
    source_url: AnyHttpUrl | None
    effective_from: date | None


class RegimeRules(RuleModel):
    standard_deduction: RuleDecimal
    hra: HraRules
    deductions: dict[str, DeductionRules]
    slabs: list[TaxSlab]
    rebate: RebateRules
    surcharge_bands: list[SurchargeBand]
    cess_rate: RuleDecimal

    @field_validator("deductions")
    @classmethod
    def require_all_deductions(cls, value: dict[str, DeductionRules]) -> dict[str, DeductionRules]:
        required = {"80C", "80D", "80CCD(1B)", "80E", "24B"}
        if set(value) != required:
            raise ValueError(f"Regime must define exactly {sorted(required)!r}")
        return value


class RulesetVersion(RuleModel):
    act: str = Field(min_length=1)
    version: str = Field(min_length=1)
    financial_year: str = Field(min_length=1)
    effective_from: date | None
    regimes: dict[Literal["old", "new"], RegimeRules]
    suggestion_terms: dict[str, SuggestionTerms] = Field(default_factory=dict)

    @field_validator("regimes")
    @classmethod
    def require_both_regimes(
        cls, value: dict[Literal["old", "new"], RegimeRules]
    ) -> dict[Literal["old", "new"], RegimeRules]:
        if set(value) != {"old", "new"}:
            raise ValueError("Ruleset must contain exactly the old and new regimes")
        return value

    def require_ready(self, regime_name: Literal["old", "new"] | None = None) -> None:
        problems: list[str] = []
        if regime_name is not None and regime_name not in self.regimes:
            raise RuleConfigurationError(f"Ruleset has no {regime_name!r} regime")
        regimes = (
            {regime_name: self.regimes[regime_name]} if regime_name is not None else self.regimes
        )

        for path, rule in _walk_rules(regimes):
            if rule.status != "verified":
                problems.append(f"{path} is not verified")
                continue
            if rule.value is None and not path.endswith(".upper_bound"):
                problems.append(f"{path} has no verified value")
            if rule.source_url is None:
                problems.append(f"{path} has no source_url")
            elif not _is_official_host(rule.source_url.host):
                problems.append(f"{path} source_url is not on an official tax domain")
            if rule.effective_from is None:
                problems.append(f"{path} has no effective_from date")

        if self.effective_from is None:
            problems.append("ruleset has no effective_from date")
        if problems:
            raise RuleConfigurationError(
                f"Ruleset {self.version!r} is not calculation-ready: " + "; ".join(problems)
            )

        self._validate_slab_structure(regimes)
        self._validate_rates(regimes)

    def require_suggestion_terms_ready(self) -> None:
        required = {
            "80C_ELSS",
            "80C_PPF",
            "80D",
            "80CCD(1B)",
            "80E",
            "24B",
            "HRA",
        }
        missing = required - self.suggestion_terms.keys()
        problems = [f"suggestion_terms.{key} is missing" for key in sorted(missing)]
        for key in sorted(required & self.suggestion_terms.keys()):
            terms = self.suggestion_terms[key]
            if terms.status != "verified":
                problems.append(f"suggestion_terms.{key} is not verified")
            if not terms.lock_in_period:
                problems.append(f"suggestion_terms.{key}.lock_in_period is missing")
            if not terms.liquidity_note:
                problems.append(f"suggestion_terms.{key}.liquidity_note is missing")
            if terms.source_url is None or not _is_official_host(terms.source_url.host):
                problems.append(f"suggestion_terms.{key}.source_url is not official")
            if terms.effective_from is None:
                problems.append(f"suggestion_terms.{key}.effective_from is missing")
        if problems:
            raise RuleConfigurationError(
                f"Ruleset {self.version!r} has incomplete suggestion terms: "
                + "; ".join(problems)
            )

    @staticmethod
    def _validate_slab_structure(regimes: dict[str, RegimeRules]) -> None:
        for regime_name, regime in regimes.items():
            if not regime.slabs:
                raise RuleConfigurationError(f"{regime_name} regime must define at least one slab")

            slabs = regime.slabs
            for index, slab in enumerate(slabs):
                lower = slab.lower_bound.value
                upper = slab.upper_bound.value
                if lower is None:
                    raise RuleConfigurationError(
                        f"{regime_name} slab {index} lower_bound cannot be open-ended"
                    )
                if index == 0 and lower != Decimal("0"):
                    raise RuleConfigurationError(f"{regime_name} first slab must start at zero")
                if upper is not None and upper <= lower:
                    raise RuleConfigurationError(
                        f"{regime_name} slab {index} upper_bound must exceed lower_bound"
                    )
                if index > 0:
                    previous_upper = slabs[index - 1].upper_bound.value
                    if previous_upper != lower:
                        raise RuleConfigurationError(
                            f"{regime_name} slab {index} is not contiguous with the prior slab"
                        )
                if index < len(slabs) - 1 and upper is None:
                    raise RuleConfigurationError(
                        f"{regime_name} only the final slab may have an open upper_bound"
                    )
                if index == len(slabs) - 1 and upper is not None:
                    raise RuleConfigurationError(
                        f"{regime_name} final slab must have an open upper_bound"
                    )

    @staticmethod
    def _validate_rates(regimes: dict[str, RegimeRules]) -> None:
        for regime_name, regime in regimes.items():
            rates = [slab.rate.value for slab in regime.slabs]
            rates.extend(band.rate.value for band in regime.surcharge_bands)
            rates.append(regime.cess_rate.value)
            rates.extend(
                (
                    regime.hra.rent_less_percent.value,
                    regime.hra.metro_salary_percent.value,
                    regime.hra.non_metro_salary_percent.value,
                )
            )
            if any(rate is not None and rate > Decimal("1") for rate in rates):
                raise RuleConfigurationError(
                    f"{regime_name} contains a rate or percentage greater than 1"
                )
            if not regime.surcharge_bands:
                raise RuleConfigurationError(
                    f"{regime_name} regime must define at least one surcharge band"
                )
            thresholds = [band.threshold.value for band in regime.surcharge_bands]
            if any(threshold is None for threshold in thresholds):
                raise RuleConfigurationError(f"{regime_name} has an open surcharge threshold")
            if thresholds != sorted(set(thresholds)):
                raise RuleConfigurationError(
                    f"{regime_name} surcharge thresholds must be unique and sorted"
                )


class RulesDocument(RuleModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    schema_uri: str | None = Field(default=None, alias="$schema")
    schema_version: Literal[1]
    act: str = Field(min_length=1)
    versions: list[RulesetVersion] = Field(min_length=1)


def _walk_rules(value: object, prefix: str = "") -> list[tuple[str, RuleDecimal | RuleBoolean]]:
    found: list[tuple[str, RuleDecimal | RuleBoolean]] = []
    if isinstance(value, (RuleDecimal, RuleBoolean)):
        return [(prefix, value)]
    if isinstance(value, BaseModel):
        for name in type(value).model_fields:
            child = getattr(value, name)
            child_prefix = f"{prefix}.{name}" if prefix else name
            found.extend(_walk_rules(child, child_prefix))
    elif isinstance(value, dict):
        for name, child in value.items():
            child_prefix = f"{prefix}.{name}" if prefix else str(name)
            found.extend(_walk_rules(child, child_prefix))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_walk_rules(child, f"{prefix}[{index}]"))
    return found


def _is_official_host(host: str) -> bool:
    normalized_host = host.lower().rstrip(".")
    return any(
        normalized_host == official_host or normalized_host.endswith(f".{official_host}")
        for official_host in OFFICIAL_SOURCE_HOSTS
    )


def is_official_source(host: str) -> bool:
    return _is_official_host(host)


def load_rules(
    financial_year: str,
    *,
    act: str = "Income-tax Act, 2025",
    path: Path = RULES_FILE,
) -> RulesetVersion:
    """Parse and select one Act/FY ruleset; unverified values remain non-executable."""
    try:
        document_data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(document_data, dict):
            raise TypeError("Rules document root must be an object")
        document = RulesDocument.model_validate(
            {
                **document_data,
                "versions": [
                    {**version, "act": document_data["act"]}
                    for version in document_data["versions"]
                ],
            }
        )
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValidationError) as error:
        raise RuleConfigurationError(f"Unable to load valid rules from {path}") from error

    if document.act != act:
        raise RuleConfigurationError(
            f"Rules file contains {document.act!r}, not requested Act {act!r}"
        )
    matches = [version for version in document.versions if version.financial_year == financial_year]
    if not matches:
        raise RuleConfigurationError(f"No rules for {act!r}, financial year {financial_year!r}")
    if len(matches) > 1:
        raise RuleConfigurationError(
            f"Multiple versions found for {act!r}, financial year {financial_year!r}"
        )
    return matches[0]
