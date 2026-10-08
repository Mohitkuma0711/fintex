---
applyTo: "backend/app/services/tax_engine/**,backend/app/rules/**"
---

# Tax engine and rules instructions

- Implement the tax engine as pure deterministic functions: same validated
  inputs and rule version must always yield the same result.
- Use `Decimal` for every monetary amount; never use `float`.
- Keep all rates, thresholds, slabs, and effective dates in versioned
  JSON/YAML under `backend/app/rules/`, not hardcoded in calculation code.
- Record a trace entry for every calculation step, including input, operation,
  output, and applicable rule reference.
- Every result must support a plain-language “Why?” explanation and identify the
  rules version used.
- Never call an LLM to compute, adjust, or validate tax amounts.
- Add complete unit and golden-case coverage for every rule and boundary.
