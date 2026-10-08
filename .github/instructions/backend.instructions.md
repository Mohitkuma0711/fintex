---
applyTo: "backend/**"
---

# Backend instructions

- Target Python 3.12, FastAPI, and Pydantic v2.
- Preserve the layered structure: API routes validate/route requests; services
  coordinate; repositories persist; models describe persistence; schemas define
  API contracts.
- Keep secrets in environment configuration and never log PII, document content,
  or sensitive extracted values.
- Use async I/O where it fits the existing interface and make external failures
  explicit.
- Add tests under the corresponding `backend/tests/` category and run Ruff.
- See `tax-engine.instructions.md` for additional rules-engine constraints.
