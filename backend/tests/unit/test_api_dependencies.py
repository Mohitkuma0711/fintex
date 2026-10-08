from pathlib import Path

import pytest
from fastapi import HTTPException

from app.api.v1.dependencies import require_configured_rules
from app.core.config import Settings
from app.services.tax_engine import rules as rules_module
from tests.unit.tax_engine_fixtures import build_test_rules


def test_rules_selector_refuses_unverified_rules_and_does_not_leak_rule_details(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    incomplete = build_test_rules()
    incomplete.regimes["old"].standard_deduction.status = "TODO"
    monkeypatch.setattr(rules_module, "load_rules", lambda *_args, **_kwargs: incomplete)
    selector = require_configured_rules(Settings(tax_rules_file=Path("test-rules.json")))
    with pytest.raises(HTTPException) as raised:
        selector("Synthetic FY")

    assert raised.value.status_code == 503
    assert "Verified tax rules" in raised.value.detail
    assert "standard_deduction" not in raised.value.detail
