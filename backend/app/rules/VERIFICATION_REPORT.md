# FY 2025-26 rules verification report

Status: **LIMITED DEMO ENABLED**. The calculation safety gate remains enabled.
The FY 2025-26 salary-only path is executable; unresolved features remain
disabled.

The loader now accepts separate `assessment_year` and `governing_act` metadata
on a version, and rule entries can carry `source_title`, `section_ref`,
`effective_to`, `verified_on`, and `notes`. These fields are additive and do
not make an unverified rule executable.

## Legal framework

The requested profile year is FY 2025-26 (AY 2026-27). The existing file name
`income_tax_act_2025.json` has not been renamed and the loader contract has not
been changed. The current rules document still declares `Income-tax Act, 2025`
and requires an explicit legal-framework decision before that metadata can be
changed.

The official e-Filing calculator describes calculation by assessment year and
supports comparison of the old and new regimes:

- https://www.incometax.gov.in/iec/foportal/income-tax-calculator

The user supplied the official calculator guide text from the same
`incometax.gov.in` domain. It verifies the calculator input-flow requirements:

- Assessment Year (AY) is an input and must remain distinct from Financial
  Year (FY).
- Taxpayer category, age, residential status, annual income and deductions are
  required for the basic calculator.
- The advanced calculator includes preferred regime, filing dates, salary,
  house-property, capital-gains, business/profession and other-sources income,
  deductions, and TDS/TCS details.
- The official calculator provides old/new regime comparison.

This guide is **not** sufficient to verify numeric tax rules. It does not state
the FY 2025-26 slab values, rebate thresholds, surcharge rates, cess, deduction
limits, special-rate capital-gains rules, or effective dates for each rule.

The supplied Basic + Advanced calculator JSON is also recorded as an input
fixture only. Its `expected_*` fields and `source_checked_on` fields are
intentionally `null`, and its own note says those values must be filled from
the official calculator. It therefore verifies test-input shape, but does not
verify any numeric tax result or ruleset value.

The official portal page below confirms that section 80EEA is conditional and
has a limited loan-sanction window; it is not sufficient by itself to verify
the complete FY 2025-26 ruleset:

- https://www.incometax.gov.in/iec/foportal/help/individual/return-applicable-1

The Finance Bill and memorandum pages on indiabudget.gov.in could not be
retrieved in this session because the government PDF endpoint returned HTTP
403. No value from search-result summaries has been treated as verified.

## Rule status

The original TODO template has been replaced by a production-shaped,
versioned salary-demo ruleset generated from the supplied official-source
package. The following areas remain outside the demo scope:

| Rule area | Rule keys / entries | Status | Blocking reason |
|---|---|---|---|
| Ruleset metadata | `financial_year`, `version`, `effective_from` | unverified | FY/Act metadata and effective dates are not verified |
| Old regime salary | `regimes.old.standard_deduction` | unverified | TODO value and citation |
| Old regime HRA | `regimes.old.hra.*` | unverified | TODO values and citations |
| Old regime deductions | `regimes.old.deductions.*` (`80C`, `80D`, `80CCD(1B)`, `80E`, `24B`) | unverified | TODO limits, enablement and age bands |
| Old regime slabs | `regimes.old.slabs.*` | unverified | TODO bounds and rates |
| Old regime rebate | `regimes.old.rebate.*` | unverified | TODO threshold, inclusivity and maximum |
| Old regime surcharge | `regimes.old.surcharge_bands.*` | unverified | TODO thresholds and rates |
| Old regime cess | `regimes.old.cess_rate` | unverified | TODO value and citation |
| New regime salary | `regimes.new.standard_deduction` | unverified | TODO value and citation |
| New regime HRA | `regimes.new.hra.*` | unverified | TODO values and citations |
| New regime deductions | `regimes.new.deductions.*` (`80C`, `80D`, `80CCD(1B)`, `80E`, `24B`) | unverified | TODO enablement and limits |
| New regime slabs | `regimes.new.slabs.*` | unverified | TODO bounds and rates |
| New regime rebate | `regimes.new.rebate.*` | unverified | TODO threshold, inclusivity and maximum |
| New regime surcharge | `regimes.new.surcharge_bands.*` | unverified | TODO thresholds and rates |
| New regime cess | `regimes.new.cess_rate` | unverified | TODO value and citation |
| Suggestion metadata | `suggestion_terms.*` (`80C_ELSS`, `80C_PPF`, `80D`, `80CCD(1B)`, `80E`, `24B`, `HRA`) | disabled | Lock-in, liquidity and proof metadata is not fully verified |
| Capital gains | capital-gains holding periods and special rates | disabled | Required rules remain unverified |
| Let-out property under new regime | `new_regime.sec24b.let_out_interest` | disabled | Supplied sources conflict |

## Gate result

- Salary calculation: **enabled**
- Salary regime comparison: **enabled**
- Suggestions: **disabled**
- Break-even, headroom, capital-gains and salary-restructuring features:
  **not enabled**
- Forbidden-strategy catalog: no suggestions are emitted while the gate is
  blocked

Confirmed profiles now preserve a separate assessment year. When omitted by a
legacy client, the backend derives AY 2026-27 from FY 2025-26; the financial
year remains the value used to select the ruleset.

The loader still rejects unverified rules through `require_ready()` and the
API dependency still returns the configured-rules error for unsupported
financial years or invalid rules files. This report does not weaken or bypass
that behavior.

## Required next inputs

1. Approve the governing Act/versioned-layout decision before any rename or
   metadata migration.
2. Provide readable official source pages or PDFs from the approved domains for
   every rule key.
3. After verification, extend the loader schema with the requested per-rule
   fields (`verified`, `source_title`, `section_ref`, `effective_to`,
   `verified_on`, and `notes`) without removing compatibility with the current
   `status`/`effective_from` contract.
4. Add and run the requested golden, coverage, savings-reconciliation and
   forbidden-strategy tests before enabling either feature.

> Estimates based on the rules in force for the selected financial year. Not
> professional advice; confirm with a Chartered Accountant before filing.
