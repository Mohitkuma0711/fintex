---
name: add-tax-rule
description: Add a versioned tax rule and deterministic calculation coverage.
---

Add the requested tax rule as versioned JSON/YAML under `backend/app/rules/`.
Update only the deterministic tax-engine code needed to consume rule data. Use
Decimal, provide a trace and plain-language “Why?” for each step, and add unit,
boundary, and golden-case tests. Never ask Gemini to calculate or hardcode a tax
parameter in Python.
