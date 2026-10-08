from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.tax import TaxComparisonResult


class SuggestionModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SuggestionResponse(SuggestionModel):
    id: UUID
    key: str
    title: str
    product: str
    amount_to_invest: Decimal
    lock_in_period: str
    liquidity_note: str
    tax_saved: Decimal
    net_benefit: Decimal
    eligible_regime: Literal["old", "new"] | None
    alternative_group: str | None
    rule_reference: str
    explanation: str
    explanation_source: Literal["gemini", "template"]
    before: TaxComparisonResult
    after: TaxComparisonResult
    planned_to_do: bool
