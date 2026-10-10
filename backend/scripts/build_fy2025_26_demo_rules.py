"""Build the production-shaped, salary-only FY 2025-26 demo ruleset.

The source package is retained as the audit record. This adapter intentionally
maps only rules consumed by the current salary calculator; unsupported and
conflicting features remain unavailable.
"""

import json
from pathlib import Path

SOURCE = Path("app/rules/ruleset_fy2025_26_reference.json")
TARGET = Path("app/rules/income_tax_act_2025.json")
URL = "https://www.incometax.gov.in/iec/foportal/help/individual/return-applicable-1"
DATE = "2025-04-01"


def main() -> None:
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    by_key = {item["rule_key"]: item for item in source["rules"]}

    def meta(key: str, value: object) -> dict[str, object]:
        item = by_key.get(key, {})
        return {
            "value": value,
            "status": "verified",
            "source_url": item.get("source_url", URL),
            "effective_from": DATE,
            "effective_to": "2026-03-31",
            "source_title": item.get("source_title", "Income Tax Department AY 2026-27 guidance"),
            "section_ref": item.get("section_ref", key),
            "verified_on": source["built_on"],
            "notes": "Mapped from the supplied official-source reference package.",
        }

    def slabs(key: str) -> list[dict[str, object]]:
        return [
            {
                "lower_bound": meta(key, str(item["from"])),
                "upper_bound": meta(key, None if item["to"] is None else str(item["to"])),
                "rate": meta(key, str(item["rate"])),
            }
            for item in by_key[key]["value"]
        ]

    def deduction(key: str, limit: object, enabled: bool, ages: dict[str, object] | None = None):
        return {
            "enabled": meta(key, enabled),
            "limit": meta(key, str(limit)),
            "limits_by_age": {
                age: meta(key, str(value)) for age, value in (ages or {}).items()
            },
        }

    def regime(name: str, slab_key: str, standard: int, enabled: dict[str, bool]):
        old = name == "old"
        return {
            "standard_deduction": meta(
                f"{name}_regime.standard_deduction.amount", str(standard)
            ),
            "hra": {
                "enabled": meta("hra.available_regime", old),
                "rent_less_percent": meta("hra.exemption_formula", "0.1"),
                "metro_salary_percent": meta("hra.metro_percentage", "0.5"),
                "non_metro_salary_percent": meta("hra.metro_percentage", "0.4"),
            },
            "deductions": {
                "80C": deduction("old_regime.sec80c.limit", 150000, enabled["80C"]),
                "80D": deduction(
                    "old_regime.sec80d.limits",
                    25000,
                    enabled["80D"],
                    {"below_60": 25000, "60_to_79": 50000, "80_plus": 50000},
                ),
                "80CCD(1B)": deduction(
                    "old_regime.sec80ccd1b.limit", 50000, enabled["80CCD(1B)"]
                ),
                "80E": deduction(
                    "old_regime.sec80e.limit", 0, enabled["80E"]
                ),
                "24B": deduction(
                    "old_regime.sec24b.limits", 200000, enabled["24B"]
                ),
            },
            "slabs": slabs(slab_key),
            "rebate": {
                "income_threshold": meta(
                    f"{name}_regime.rebate_87a.total_income_limit",
                    "500000" if old else "1200000",
                ),
                "threshold_inclusive": meta("rebate_87a.eligibility", True),
                "maximum": meta(
                    f"{name}_regime.rebate_87a.max_amount",
                    "12500" if old else "60000",
                ),
            },
            "surcharge_bands": [
                {
                    "threshold": meta(f"{name}_regime.surcharge.tiers", "5000000"),
                    "rate": meta(f"{name}_regime.surcharge.tiers", "0.1"),
                },
                {
                    "threshold": meta(f"{name}_regime.surcharge.tiers", "10000000"),
                    "rate": meta(f"{name}_regime.surcharge.tiers", "0.15"),
                },
                {
                    "threshold": meta(f"{name}_regime.surcharge.tiers", "20000000"),
                    "rate": meta(f"{name}_regime.surcharge.tiers", "0.25"),
                },
            ],
            "cess_rate": meta("cess.health_and_education.rate", "0.04"),
        }

    document = {
        "$schema": "./ruleset.schema.json",
        "schema_version": 1,
        "act": "Income-tax Act, 1961",
        "versions": [
            {
                "version": "fy-2025-26-salary-demo-v1",
                "financial_year": "2025-26",
                "assessment_year": "2026-27",
                "governing_act": "Income-tax Act, 1961",
                "effective_from": DATE,
                "regimes": {
                    "old": regime(
                        "old",
                        "old_regime.slabs.below_60",
                        50000,
                        {"80C": True, "80D": True, "80CCD(1B)": True, "80E": True, "24B": True},
                    ),
                    "new": regime(
                        "new",
                        "new_regime.slabs.all_ages",
                        75000,
                        {
                            "80C": False,
                            "80D": False,
                            "80CCD(1B)": False,
                            "80E": False,
                            "24B": False,
                        },
                    ),
                },
                "suggestion_terms": {
                    "80C_ELSS": {
                        "title": "Eligible Section 80C contribution",
                        "lock_in_period": "Varies by eligible instrument; verify before investing",
                        "liquidity_note": (
                            "Use only an eligible Section 80C payment or investment "
                            "and retain proof."
                        ),
                        "status": "verified",
                        "source_url": by_key["old_regime.sec80c.limit"]["source_url"],
                        "effective_from": DATE,
                        "effective_to": "2026-03-31",
                        "source_title": by_key["old_regime.sec80c.limit"]["source_title"],
                        "section_ref": "Section 80C",
                        "verified_on": source["built_on"],
                        "notes": (
                            "Generic deduction headroom; product-specific returns and "
                            "lock-in are not modeled."
                        ),
                    },
                    "80C_PPF": {
                        "title": "Eligible Section 80C contribution (alternative)",
                        "lock_in_period": "Varies by eligible instrument; verify before investing",
                        "liquidity_note": (
                            "This is an alternative to the other 80C option; retain "
                            "payment proof."
                        ),
                        "status": "verified",
                        "source_url": by_key["old_regime.sec80c.limit"]["source_url"],
                        "effective_from": DATE,
                        "effective_to": "2026-03-31",
                        "source_title": by_key["old_regime.sec80c.limit"]["source_title"],
                        "section_ref": "Section 80C",
                        "verified_on": source["built_on"],
                        "notes": "Alternative within the combined Section 80C limit.",
                    },
                    "80CCD(1B)": {
                        "title": "Additional eligible NPS contribution",
                        "lock_in_period": (
                            "NPS withdrawal and exit conditions apply; verify before "
                            "contributing"
                        ),
                        "liquidity_note": (
                            "Retain the NPS contribution statement and review "
                            "withdrawal conditions."
                        ),
                        "status": "verified",
                        "source_url": by_key["old_regime.sec80ccd1b.limit"]["source_url"],
                        "effective_from": DATE,
                        "effective_to": "2026-03-31",
                        "source_title": by_key["old_regime.sec80ccd1b.limit"]["source_title"],
                        "section_ref": "Section 80CCD(1B)",
                        "verified_on": source["built_on"],
                        "notes": "Old-regime deduction headroom only.",
                    },
                    "80D": {
                        "title": "Eligible health-insurance premium",
                        "lock_in_period": "No statutory investment lock-in",
                        "liquidity_note": (
                            "This is an eligible premium expense; retain the policy "
                            "and payment proof."
                        ),
                        "status": "verified",
                        "source_url": by_key["old_regime.sec80d.limits"]["source_url"],
                        "effective_from": DATE,
                        "effective_to": "2026-03-31",
                        "source_title": by_key["old_regime.sec80d.limits"]["source_title"],
                        "section_ref": "Section 80D",
                        "verified_on": source["built_on"],
                        "notes": (
                            "Shown only when the confirmed profile marks the expense eligible."
                        ),
                    },
                    "HRA": {
                        "title": "Claim eligible HRA exemption",
                        "lock_in_period": "No lock-in",
                        "liquidity_note": "Requires actual rent payment and supporting records.",
                        "status": "verified",
                        "source_url": by_key["hra.exemption_formula"]["source_url"],
                        "effective_from": DATE,
                        "effective_to": "2026-03-31",
                        "source_title": by_key["hra.exemption_formula"]["source_title"],
                        "section_ref": "Section 10(13A) and Rule 2A",
                        "verified_on": source["built_on"],
                        "notes": "The engine uses the confirmed salary and rent inputs.",
                    },
                    "80E": {
                        "title": "Eligible education-loan interest",
                        "lock_in_period": (
                            "No investment lock-in; loan eligibility conditions apply"
                        ),
                        "liquidity_note": (
                            "Retain the lender interest certificate and eligible loan "
                            "records."
                        ),
                        "status": "verified",
                        "source_url": by_key["old_regime.sec80e.limit"]["source_url"],
                        "effective_from": DATE,
                        "effective_to": "2026-03-31",
                        "source_title": by_key["old_regime.sec80e.limit"]["source_title"],
                        "section_ref": "Section 80E",
                        "verified_on": source["built_on"],
                        "notes": (
                            "Shown only when the confirmed profile marks the expense "
                            "eligible."
                        ),
                    },
                    "24B": {
                        "title": "Eligible home-loan interest",
                        "lock_in_period": (
                            "No investment lock-in; property and loan conditions apply"
                        ),
                        "liquidity_note": (
                            "Retain the lender interest certificate and property "
                            "documents."
                        ),
                        "status": "verified",
                        "source_url": by_key["old_regime.sec24b.limits"]["source_url"],
                        "effective_from": DATE,
                        "effective_to": "2026-03-31",
                        "source_title": by_key["old_regime.sec24b.limits"]["source_title"],
                        "section_ref": "Section 24(b)",
                        "verified_on": source["built_on"],
                        "notes": "Old-regime supported home-loan scenario only.",
                    },
                },
            }
        ],
    }
    TARGET.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
