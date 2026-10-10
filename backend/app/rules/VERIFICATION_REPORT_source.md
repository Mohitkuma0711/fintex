# VERIFICATION_REPORT: FY 2025-26 (AY 2026-27)

Built 2026-10-10. Governing Act: **Income-tax Act, 1961** (Income-tax Act, 2025 starts 1 April 2026, per s.1(3) and the CBDT press release).

Totals: **53 verified**, **10 unverified**, **1 conflicting** (of 64 rules).

| Rule | Value (short) | Source URL | Status |
|---|---|---|---|
| `meta.governing_act` | "Income-tax Act, 1961" | https://www.incometaxindia.gov.in/w/section-1-1 | verified |
| `new_regime.slabs.all_ages` | [{"from": 0, "to": 400000, "rate": 0.0, "cumulative_tax_at_f... | https://www.incometax.gov.in/iec/foportal/help/individual/return-applicable-1 | verified |
| `old_regime.slabs.below_60` | [{"from": 0, "to": 250000, "rate": 0.0, "cumulative_tax_at_f... | https://www.incometax.gov.in/iec/foportal/help/individual/return-applicable-1 | verified |
| `old_regime.slabs.age_60_to_79` | [{"from": 0, "to": 300000, "rate": 0.0, "cumulative_tax_at_f... | https://www.incometax.gov.in/iec/foportal/help/individual/return-applicable-1 | verified |
| `old_regime.slabs.age_80_plus` | [{"from": 0, "to": 500000, "rate": 0.0, "cumulative_tax_at_f... | https://www.incometax.gov.in/iec/foportal/help/individual/return-applicable-1 | verified |
| `old_regime.slabs.non_resident_any_age` | [{"from": 0, "to": 250000, "rate": 0.0, "cumulative_tax_at_f... | https://www.incometaxindia.gov.in/w/tax-rates%E2%80%8B | verified |
| `meta.age_band_definition` | {"senior": "60 years or more at any time during the previous... | https://www.incometaxindia.gov.in/w/tax-rates%E2%80%8B | verified |
| `meta.default_regime` | "new regime u/s 115BAC(1A) is default; opt out under 115BAC(6)" | https://www.incometaxindia.gov.in/w/tax-rates%E2%80%8B | verified |
| `old_regime.standard_deduction.amount` | 50000 | https://www.incometaxindia.gov.in/w/section-16-228 | verified |
| `new_regime.standard_deduction.amount` | 75000 | https://www.incometaxindia.gov.in/w/section-16-228 | verified |
| `old_regime.entertainment_allowance.limit` | {"applies_to": "government employees only", "limit": "lower ... | https://www.incometaxindia.gov.in/w/section-16-228 | verified |
| `old_regime.professional_tax.deduction` | "actual tax on employment paid (Art. 276 of Constitution)" | https://www.incometaxindia.gov.in/w/section-16-228 | verified |
| `new_regime.entertainment_allowance_and_professional_tax_allowed` | false | https://www.incometaxindia.gov.in/w/tax-rates%E2%80%8B | verified |
| `new_regime.rebate_87a.total_income_limit` | 1200000 | https://www.incometaxindia.gov.in/w/section-87a-30 | verified |
| `new_regime.rebate_87a.max_amount` | 60000 | https://www.incometaxindia.gov.in/w/section-87a-30 | verified |
| `new_regime.rebate_87a.marginal_relief` | "if total income > 12,00,000 and tax > (income - 12,00,000):... | https://www.incometaxindia.gov.in/w/section-87a-30 | verified |
| `old_regime.rebate_87a.total_income_limit` | 500000 | https://www.incometaxindia.gov.in/w/section-87a-30 | verified |
| `old_regime.rebate_87a.max_amount` | 12500 | https://www.incometaxindia.gov.in/w/section-87a-30 | verified |
| `rebate_87a.eligibility` | "resident individual only; rebate deducted from tax before c... | https://www.incometaxindia.gov.in/w/section-87a-30 | verified |
| `new_regime.surcharge.tiers` | [{"income_exceeds": 5000000, "rate": 0.1}, {"income_exceeds"... | https://www.incometaxindia.gov.in/w/tax-rates%E2%80%8B | verified |
| `old_regime.surcharge.tiers` | [{"income_exceeds": 5000000, "rate": 0.1}, {"income_exceeds"... | https://www.incometaxindia.gov.in/w/tax-rates%E2%80%8B | verified |
| `surcharge.special_rate_income_cap` | 0.15 | https://www.incometaxindia.gov.in/w/tax-rates%E2%80%8B | verified |
| `surcharge.marginal_relief` | "income-tax + surcharge must not exceed tax (incl. surcharge... | https://www.incometaxindia.gov.in/w/tax-rates%E2%80%8B | verified |
| `cess.health_and_education.rate` | 0.04 | https://www.incometaxindia.gov.in/w/tax-rates%E2%80%8B | verified |
| `old_regime.sec80c.limit` | 150000 | https://www.incometax.gov.in/iec/foportal/help/individual/return-applicable-1 | verified |
| `old_regime.sec80c.eligible_items_examples` | ["life insurance premium", "provident fund", "subscription t... | https://www.incometax.gov.in/iec/foportal/help/individual/return-applicable-1 | verified |
| `old_regime.sec80ccd1.limit_pct` | {"employee": "10% of salary", "others": "20% of gross total ... | https://www.incometaxindia.gov.in/w/section-80ccd-24 | verified |
| `old_regime.sec80ccd1b.limit` | 50000 | https://www.incometaxindia.gov.in/w/section-80ccd-24 | verified |
| `old_regime.sec80ccd2.limit_pct_of_salary` | {"central_or_state_government_employer": 0.14, "any_other_em... | https://www.incometaxindia.gov.in/w/section-80ccd-24 | verified |
| `new_regime.sec80ccd2.limit_pct_of_salary` | 0.14 | https://www.incometaxindia.gov.in/w/section-80ccd-24 | verified |
| `old_regime.sec80d.limits` | {"self_spouse_children": {"normal": 25000, "senior_citizen":... | https://www.incometaxindia.gov.in/w/section-80d-60 | verified |
| `old_regime.sec80dd.limits` | {"disability": 75000, "severe_disability_80pct_or_more": 125... | https://www.incometax.gov.in/iec/foportal/help/individual/return-applicable-1 | verified |
| `old_regime.sec80ddb.limits` | {"normal": 40000, "senior_citizen": 100000} | https://www.incometax.gov.in/iec/foportal/help/individual/return-applicable-1 | verified |
| `old_regime.sec80e.limit` | "no monetary cap: total interest paid on higher-education loan" | https://www.incometax.gov.in/iec/foportal/help/individual/return-applicable-1 | verified |
| `old_regime.sec80ee.limit` | {"cap": 50000, "loan_sanctioned_between": ["2016-04-01", "20... | https://www.incometax.gov.in/iec/foportal/help/individual/return-applicable-1 | verified |
| `old_regime.sec80eea.limit` | {"cap": 150000, "loan_sanctioned_between": ["2019-04-01", "2... | https://www.incometax.gov.in/iec/foportal/help/individual/return-applicable-1 | verified |
| `old_regime.sec80eeb.limit` | {"cap": 150000, "loan_sanctioned_between": ["2019-04-01", "2... | https://www.incometax.gov.in/iec/foportal/help/individual/return-applicable-1 | verified |
| `old_regime.sec80g.cash_donation_limit` | 2000 | https://www.incometax.gov.in/iec/foportal/help/individual/return-applicable-1 | verified |
| `old_regime.sec80gg.limits` | {"monthly_cap": 5000, "pct_of_total_income": 0.25, "rent_min... | https://www.incometax.gov.in/iec/foportal/help/individual/return-applicable-1 | verified |
| `old_regime.sec80tta.limit` | 10000 | https://www.incometax.gov.in/iec/foportal/help/individual/return-applicable-1 | verified |
| `old_regime.sec80ttb.limit` | 50000 | https://www.incometax.gov.in/iec/foportal/help/individual/return-applicable-1 | verified |
| `old_regime.sec80u.limits` | {"disability": 75000, "severe_disability_80pct_or_more": 125... | https://www.incometax.gov.in/iec/foportal/help/individual/return-applicable-1 | verified |
| `old_regime.sec24b.limits` | {"self_occupied": {"loan_on_or_after_1999-04-01_purchase_or_... | https://www.incometax.gov.in/iec/foportal/help/individual/return-applicable-1 | verified |
| `new_regime.not_allowed_exemptions_and_deductions` | ["s.10(5) LTC", "s.10(13A) HRA", "s.10(14) allowances other ... | https://www.incometaxindia.gov.in/w/tax-rates%E2%80%8B | verified |
| `new_regime.allowed_deductions` | ["standard deduction s.16(ia) 75,000", "employer NPS s.80CCD... | https://www.incometax.gov.in/iec/foportal/help/individual/return-applicable-1 | verified |
| `new_regime.sec24b.let_out_interest` | null | https://www.incometax.gov.in/iec/foportal/help/individual/return-applicable-1 | conflicting |
| `hra.exemption_formula` | "least of (a) actual HRA received, (b) rent paid minus one-t... | https://www.incometaxindia.gov.in/w/rule-2a-1 | verified |
| `hra.metro_percentage` | {"Mumbai": 0.5, "Kolkata": 0.5, "Delhi": 0.5, "Chennai": 0.5... | https://www.incometaxindia.gov.in/w/rule-2a-1 | verified |
| `hra.relevant_period` | "period during which the accommodation was occupied in the p... | https://www.incometaxindia.gov.in/w/rule-2a-1 | verified |
| `hra.available_regime` | "old regime only (s.10(13A) is in the new-regime disallowed ... | https://www.incometaxindia.gov.in/w/tax-rates%E2%80%8B | verified |
| `hra.salary_definition` | null | https://www.incometaxindia.gov.in/w/rule-2a-1 | unverified |
| `hra.landlord_pan_requirement` | null |  | unverified |
| `capital_gains.sec111a.rate` | 0.2 | https://www.incometaxindia.gov.in/w/determination-of-tax-in-certain-special-cases%E2%80%8B | verified |
| `capital_gains.sec112a.rate` | 0.125 | https://www.incometaxindia.gov.in/w/determination-of-tax-in-certain-special-cases%E2%80%8B | verified |
| `capital_gains.sec112a.exemption_limit` | 125000 | https://www.incometaxindia.gov.in/w/determination-of-tax-in-certain-special-cases%E2%80%8B | verified |
| `capital_gains.sec112.rate` | 0.125 | https://www.incometaxindia.gov.in/w/determination-of-tax-in-certain-special-cases%E2%80%8B | verified |
| `capital_gains.holding_periods` | null |  | unverified |
| `rebate_87a.applicable_to_special_rate_gains` | null |  | unverified |
| `old_regime.sec80e.deduction_period_years` | null |  | unverified |
| `old_regime.sec80g.qualifying_limit_and_category_rates` | null |  | unverified |
| `family_pension.deduction` | null |  | unverified |
| `interest_and_fee.sec234a_234b_234c_234f` | null |  | unverified |
| `suggestion_meta.lock_in_and_liquidity` | null |  | unverified |
| `meta.section_mapping_1961_to_2025` | null |  | unverified |

## Conflicts and discrepancies

1. `new_regime.sec24b.let_out_interest` (**conflicting**): the e-Filing page (S1) says let-out property interest is allowed in the new regime with no loss set-off; the tax-rates page (S2) lists s.24(b) with no let-out exception. Needs your or a CA's decision.
2. s.87A new-regime threshold (resolved, please confirm): the tax-rates page note for AY 2026-27 prints a 7,00,000 limit beside the 60,000 rebate, while the statute text (s.87A, S4) and the e-Filing page (S1) both say 12,00,000. The ruleset follows the statute text. Rules carry a `conflict_note`.
3. HRA metro list: some non-official sites claim 8 metro cities from FY 2026-27. Rule 2A (S5) for FY 2025-26 names four. Four are used.

## Effective dates

Every verified rule uses 2025-04-01 to 2026-03-31, taken from the FY/AY label on the cited page (see `effective_date_basis`). The pages do not print per-rule commencement dates, so these are not statutory commencement dates. Confirm before relying on them for audits.

## Sources opened

- S1: [e-Filing portal: Salaried Individuals for AY 2026-27 (tax slabs, deductions); page last reviewed 09-Jul-2026](https://www.incometax.gov.in/iec/foportal/help/individual/return-applicable-1)
- S2: [Income Tax Dept: Tax rates (Income-tax Act, 1961 as amended by Finance Act, 2026)](https://www.incometaxindia.gov.in/w/tax-rates%E2%80%8B)
- S3: [Income-tax Act, 1961 s.16 Deductions from salaries (current text)](https://www.incometaxindia.gov.in/w/section-16-228)
- S4: [Income-tax Act, 1961 s.87A Rebate of income-tax (current text)](https://www.incometaxindia.gov.in/w/section-87a-30)
- S5: [Income-tax Rules, 1962 r.2A Limits for the purposes of s.10(13A)](https://www.incometaxindia.gov.in/w/rule-2a-1)
- S6: [Income-tax Act, 1961 s.80CCD Pension scheme contribution](https://www.incometaxindia.gov.in/w/section-80ccd-24)
- S7: [Income-tax Act, 1961 s.80D Health insurance premia](https://www.incometaxindia.gov.in/w/section-80d-60)
- S8: [Income Tax Dept: Determination of tax in certain special cases (as amended by Finance Act, 2026)](https://www.incometaxindia.gov.in/w/determination-of-tax-in-certain-special-cases%E2%80%8B)
- S9: [Income-tax Act, 2025 s.1 Short title, extent and commencement](https://www.incometaxindia.gov.in/w/section-1-1)
