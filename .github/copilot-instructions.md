# FinTax AI project guidance

FinTax AI is an Indian tax platform following **Upload → Extract → Verify →
Calculate → Suggest → Explain & Act**. The repository contains a React/Vite
frontend and a FastAPI backend.

## Non-negotiable principles

- Gemini never computes tax. All tax arithmetic is performed by a deterministic
  Python rules engine.
- Tax rules are versioned JSON/YAML data under `backend/app/rules/`; never
  hardcode rates, thresholds, or slabs in application code.
- Every calculated number needs an auditable, step-by-step trace and a
  plain-language “Why?” explanation.
- Factual answers must be grounded in the official-source RAG knowledge base and
  include citations.
- Never log personally identifiable information (PII), tax documents, secrets,
  or sensitive extracted values. Never commit secrets or real taxpayer data.

## Coding standards

- Keep the backend layered: routes, schemas, services, repositories, and models
  have distinct responsibilities.
- Validate external input at API boundaries with Pydantic v2.
- Keep tax-engine functions deterministic and side-effect free.
- Use Decimal, not binary floating point, for monetary values.
- Add focused tests for behavior and edge cases; tax rule changes need regression
  and golden-case coverage.
- Use small, typed React components and keep frontend data validation explicit.
- Surface errors clearly; do not silently substitute values or claim success
  after a failed operation.
- Follow the nearest applicable `.instructions.md` file.
