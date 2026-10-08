from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, model_validator

AgeBracket = Literal["below_60", "60_to_79", "80_plus"]
CityType = Literal["metro", "non_metro"]


def _decimal_input(value: object) -> object:
    if isinstance(value, float):
        raise ValueError("Monetary values must not be supplied as binary floats")
    return value


Money = Annotated[
    Decimal,
    BeforeValidator(_decimal_input),
    Field(ge=Decimal("0"), max_digits=24, decimal_places=4),
]


class TaxModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SalaryComponents(TaxModel):
    basic_salary: Money = Decimal("0")
    dearness_allowance: Money = Decimal("0")
    hra_received: Money = Decimal("0")
    other_allowances: Money = Decimal("0")

    @property
    def total(self) -> Decimal:
        return (
            self.basic_salary + self.dearness_allowance + self.hra_received + self.other_allowances
        )


class HRAInputs(TaxModel):
    rent_paid: Money = Decimal("0")


class DeductionsClaimed(TaxModel):
    section_80c: Money = Decimal("0")
    section_80d: Money = Decimal("0")
    section_80ccd_1b: Money = Decimal("0")
    section_80e: Money = Decimal("0")
    section_24b: Money = Decimal("0")

    def as_mapping(self) -> dict[str, Decimal]:
        return {
            "80C": self.section_80c,
            "80D": self.section_80d,
            "80CCD(1B)": self.section_80ccd_1b,
            "80E": self.section_80e,
            "24B": self.section_24b,
        }


class TaxpayerProfile(TaxModel):
    salary_components: SalaryComponents = Field(default_factory=SalaryComponents)
    hra_inputs: HRAInputs = Field(default_factory=HRAInputs)
    other_income: Money = Decimal("0")
    deductions_claimed: DeductionsClaimed = Field(default_factory=DeductionsClaimed)
    age_bracket: AgeBracket
    city_type: CityType


class PlanningEligibility(TaxModel):
    health_insurance_eligible: bool
    eligible_health_insurance_premium: Money
    education_loan_eligible: bool
    eligible_education_loan_interest: Money
    home_loan_eligible: bool
    eligible_home_loan_interest: Money


class ConfirmedTaxpayerProfile(TaxpayerProfile):
    employment_type: Literal["employee", "business_freelancer"]
    consent_given: Literal[True]
    financial_year: str = Field(pattern=r"^\d{4}-\d{2}$")
    planning_eligibility: PlanningEligibility

    def to_taxpayer_profile(self) -> TaxpayerProfile:
        return TaxpayerProfile.model_validate(
            self.model_dump(
                exclude={
                    "employment_type",
                    "consent_given",
                    "financial_year",
                    "planning_eligibility",
                }
            )
        )

    @model_validator(mode="before")
    @classmethod
    def require_explicit_inputs(cls, value: object) -> object:
        if not isinstance(value, dict):
            raise ValueError("A taxpayer profile object is required.")
        required = {
            "employment_type",
            "consent_given",
            "financial_year",
            "planning_eligibility",
            "salary_components",
            "hra_inputs",
            "other_income",
            "deductions_claimed",
            "age_bracket",
            "city_type",
        }
        missing = required - value.keys()
        if missing:
            raise ValueError(
                f"Required confirmed profile fields are missing: {', '.join(sorted(missing))}."
            )
        if value.get("consent_given") is not True:
            raise ValueError("Explicit consent is required before confirming a taxpayer profile.")

        money_groups = {
            "salary_components": (
                "basic_salary",
                "dearness_allowance",
                "hra_received",
                "other_allowances",
            ),
            "hra_inputs": ("rent_paid",),
            "deductions_claimed": (
                "section_80c",
                "section_80d",
                "section_80ccd_1b",
                "section_80e",
                "section_24b",
            ),
        }
        amount_values: list[tuple[str, object]] = [("other_income", value.get("other_income"))]
        for group, keys in money_groups.items():
            grouped_values = value.get(group)
            if not isinstance(grouped_values, dict):
                raise ValueError(f"{group} must be an object containing decimal-string amounts.")
            amount_values.extend((f"{group}.{key}", grouped_values.get(key)) for key in keys)
        for field_name, amount in amount_values:
            if not isinstance(amount, (str, Decimal)):
                raise ValueError(f"{field_name} must be supplied as a decimal string.")
        planning = value.get("planning_eligibility")
        if not isinstance(planning, dict):
            raise ValueError("planning_eligibility must be an object.")
        for field_name in (
            "health_insurance_eligible",
            "education_loan_eligible",
            "home_loan_eligible",
        ):
            if not isinstance(planning.get(field_name), bool):
                raise ValueError(f"planning_eligibility.{field_name} must be explicitly confirmed.")
        for field_name in (
            "eligible_health_insurance_premium",
            "eligible_education_loan_interest",
            "eligible_home_loan_interest",
        ):
            if not isinstance(planning.get(field_name), (str, Decimal)):
                raise ValueError(
                    f"planning_eligibility.{field_name} must be supplied as a decimal string."
                )
        return value


class TraceStep(TaxModel):
    label: str
    formula: str
    inputs: dict[str, Decimal | str | None]
    output: Decimal
    rule_reference: str
    plain_language_why: str


class TaxResult(TaxModel):
    regime: Literal["old", "new"]
    act: str
    financial_year: str
    rules_version: str
    gross_income: Decimal
    standard_deduction: Decimal
    hra_exemption: Decimal
    deductions: dict[str, Decimal]
    taxable_income: Decimal
    tax_before_rebate: Decimal
    rebate: Decimal
    surcharge: Decimal
    cess: Decimal
    total_tax: Decimal
    trace: list[TraceStep]


class TaxComparisonResult(TaxModel):
    old_regime: TaxResult
    new_regime: TaxResult
    recommended_regime: Literal["old", "new"]
    saving: Decimal
