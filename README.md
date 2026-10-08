# FinTax AI

FinTax AI is an Indian tax-planning platform built around the workflow
**Upload → Extract → Verify → Calculate → Suggest → Explain & Act**.

The repository contains a React/Vite frontend and a FastAPI backend. It includes
private document-upload and extraction flows, profile confirmation, a
deterministic tax engine with auditable traces, regime comparison, tax-saving
scenario suggestions, and a what-if simulator.

## Project layout

- `backend/`: Python 3.12, FastAPI, SQLAlchemy, Alembic, tests, and versioned
  tax rules.
- `frontend/`: React, TypeScript, Vite, Tailwind, and responsive application UI.
- `docs/`: architecture and architecture decision records.
- `.github/`: Copilot project guidance and coding prompts.

## Local development

### Backend

Requires Python 3.12 and PostgreSQL for normal development. Install with
[uv](https://docs.astral.sh/uv/):

```bash
cd backend
uv sync --extra dev
cp .env.example .env
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

Configure the database, Supabase, and optional Gemini settings in `backend/.env`.
The API is available at `http://localhost:8000`; health check:
`http://localhost:8000/api/v1/health`.

Run backend checks:

```bash
cd backend
uv run ruff check .
uv run pytest
```

### Frontend

Requires Node.js 20.19+ or 22.12+:

```bash
cd frontend
npm ci
cp .env.example .env
npm run dev
```

Set the API base URL and public Supabase project settings in `frontend/.env`.
Run frontend checks with `npm run lint` and `npm run build`.

## Important tax-rule status

**Do not use this project to file a return or treat its outputs as tax advice.**
The checked-in rule file contains explicit TODO placeholders. The calculation,
comparison, simulator, and suggestions endpoints fail closed until the
applicable rules and suggestion terms are verified against official sources
and versioned for the relevant financial year. See
`backend/app/rules/README.md` for the verification process.

Tax calculations must remain deterministic and use `Decimal`; Gemini may only
help explain engine-provided results. Tax rules belong in versioned data, not
application code. Every calculated amount should have a trace and a
plain-language explanation. Never log taxpayer PII, documents, sensitive
financial values, or secrets.

FinTax AI is guidance, not professional tax advice. Consult a qualified
professional for advice specific to your circumstances.
