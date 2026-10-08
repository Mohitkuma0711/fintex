import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from app.schemas.tax import TaxpayerProfile
from app.services.tax_engine import compare_regimes, load_rules

FIXTURE_PATHS = sorted(Path(__file__).parent.glob("*.json"))


def read_cases() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for path in FIXTURE_PATHS:
        if path.name == "golden_case.schema.json":
            continue
        case = json.loads(path.read_text(encoding="utf-8"))
        cases.append(case)
    return cases


@pytest.mark.parametrize("case", read_cases(), ids=lambda case: case["case_id"])
def test_hand_verified_golden_case(case: dict[str, Any]) -> None:
    if case["status"] != "verified":
        pytest.skip("Golden case is a TODO placeholder until hand-verified.")

    rules = load_rules(case["financial_year"], act=case["act"])
    result = compare_regimes(TaxpayerProfile.model_validate(case["profile"]), rules)
    expected = case["expected"]

    assert result.old_regime.total_tax == Decimal(expected["old_regime_tax"])
    assert result.new_regime.total_tax == Decimal(expected["new_regime_tax"])
    assert result.recommended_regime == expected["recommended_regime"]
    assert result.saving == Decimal(expected["saving"])
