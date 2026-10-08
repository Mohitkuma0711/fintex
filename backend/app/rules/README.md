# Versioned income-tax rules

`income_tax_act_2025.json` is a deliberately incomplete, schema-checked rules
template. **It is not usable for tax calculations.** All values are `null`,
their status is `TODO`, and calculations must refuse the ruleset until every
applicable entry has been researched, recorded, and reviewed. No slab, limit,
rebate, rate, or effective date has been inferred from memory.

## Schema and versioning

- The JSON structure is defined in [`ruleset.schema.json`](./ruleset.schema.json)
  and parsed again by the backend's Pydantic rules models.
- Decimal values must be JSON strings (for example `"1234.56"`); do not use JSON
  floating-point numbers.
- A file can contain multiple `versions`, each identified by its `version`,
  `financial_year`, `effective_from`, and Act. Add a new version for a changed
  law or financial year; do not overwrite a ruleset already used for a result.
- Each individual value has `source_url`, `effective_from`, and `status`
  metadata. While unknown, keep `value`, `source_url`, and `effective_from`
  null, and status `TODO`.

## How to fill and verify each value

For each TODO, locate the provision, rule, notification, or official return
guidance applicable to the selected financial year on the Income Tax Department
portal:

- Income Tax Department portal: <https://www.incometax.gov.in/iec/foportal/>
- Income Tax Department tax-laws index:
  <https://incometaxindia.gov.in/Pages/acts/income-tax-act.aspx>

Use a direct official page or document URL for the specific provision, not just
the portal home page. Record the exact applicability and effective date stated
by that source. Put that URL and effective date on **each individual rule
entry**; a section-wide citation is not sufficient.

Before changing `status` to `verified`:

1. Have a second reviewer compare the value and its conditions against the
   linked official text for that financial year.
2. Confirm whether the rule differs between regimes, age brackets, or metro /
   non-metro categories, and encode those differences in the corresponding
   regime-specific or category-specific entry.
3. Confirm slab ranges are contiguous, non-overlapping, and have exactly one
   final open-ended range (`upper_bound.value: null` with status `verified` and
   full source/effective-date metadata).
4. Check the entry's effective date against the containing ruleset's financial
   year. Do not assume enactment date and effective date are interchangeable.
5. Add an official-source citation and reviewed, hand-calculated golden case
   for each changed boundary.
6. Set a unique rules version and run the rules-loader, unit, golden-case, and
   coverage test suites. Never enable calculations while any applicable value
   remains TODO.

### Rule coverage in the template

Both old and new regime sections have separate entries for standard deduction,
HRA availability and its three exemption parameters, 80C, 80D (with age-bracket
limits), 80CCD(1B), 80E, 24B, slab boundaries and rates, rebate eligibility and
maximum, surcharge thresholds and rates, and cess rate.

For each regime, verify every parameter independently. If a provision does not
apply, set its `enabled.value` to `false` and cite the official basis; do not
leave it TODO or silently treat a missing value as zero. Fill age-specific
80D limits only where the official rule requires them. The rules loader rejects
missing metadata, and calculation code rejects entries not explicitly
verified.

Suggestion product terms use `suggestion_terms` in each ruleset version. Verify
each lock-in period and liquidity note against an official source for the
financial year, then add that source URL and effective date and set status to
`verified`. Suggestions remain unavailable while any required term is TODO.
The 80C ELSS and PPF options share the same deduction allowance; they are
alternatives and their potential savings must not be added together.
Each suggestion's impact is the difference between independent baseline and
scenario runs of both regimes. Health-insurance, education-loan, and home-loan
scenarios additionally require explicit confirmed eligibility and eligible
amounts from the taxpayer. "Net benefit" means tax saved only; investment
returns, fees, liquidity value, and opportunity cost are not estimated.
The simulator applies one requested change to a copy of the confirmed
calculation inputs and returns both engine results and their tax difference.

## Scope and caution

These data are inputs to a deterministic calculation engine, not legal advice.
`TODO` placeholder values must never be used to produce or imply a tax result.
