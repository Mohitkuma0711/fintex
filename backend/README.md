# FinTax AI backend

FastAPI backend for Python 3.12 with async SQLAlchemy persistence, Supabase JWT
verification, and a deterministic tax-engine API.

```bash
uv sync --extra dev
cp .env.example .env
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --no-access-log
```

Copy `.env.example` to `.env` for local configuration. Never commit `.env` or
place sensitive values in logs. Configure `SUPABASE_URL` for authenticated
routes. Legacy HS256 projects also need `SUPABASE_JWT_SECRET`; asymmetric
signing keys are fetched from
`<SUPABASE_URL>/auth/v1/.well-known/jwks.json`. The frontend needs the public
project URL and anon key in `../frontend/.env.local`.

Money fields in API requests should be decimal strings (for example `"1250.50"`)
so binary floating-point input cannot enter the tax calculation path.

OpenAPI docs are served at `/docs`; the importable Postman collection is
`../docs/postman/FinTax-AI.postman_collection.json`. Tax calculations fail closed
while the checked-in rules file still contains TODO values. Set
`TAX_RULES_FILE` to a reviewed, complete ruleset before enabling those routes.

### Private document extraction

Set `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` to enable document storage.
Uploads use the configured `SUPABASE_STORAGE_BUCKET`; the API verifies that the
bucket is private and creates it as private if it does not exist. Keep the
service-role key server-side and never put it in frontend configuration. Uploads
are limited by `MAX_UPLOAD_SIZE_BYTES` and accept PDF, JPG, and PNG files only.
The API returns an expiring signed URL; document listings do not expose storage
URLs.

Set `GOOGLE_API_KEY` to enable Gemini-backed extraction. `GEMINI_MODEL`,
`GEMINI_TIMEOUT_SECONDS`, `GEMINI_MAX_ATTEMPTS`, and
`EXTRACTION_MAX_PDF_PAGES` configure the provider and processing limits.
Text-based PDFs are parsed with pdfplumber before structured extraction; scanned
PDFs and images are sent to Gemini as multimodal input. The versioned prompts
instruct Gemini to extract visible values only and return null for unknowns.
Gemini does not calculate tax.

The authenticated `POST /api/v1/documents` endpoint starts extraction in a
background task. Poll `GET /api/v1/documents/{id}/extraction` for the document
and extraction status; retry failed jobs with
`POST /api/v1/documents/{id}/retry`. The virus scanner is currently a hook
placeholder (`not_scanned`), not malware protection. Do not represent uploaded
documents as scanned until a real scanner is configured.

### Verify and confirm

The review workflow exposes automatic checks at
`GET /api/v1/extractions/{id}/validation` and saves corrected values plus an
explicitly consented confirmed profile at
`PUT /api/v1/extractions/{id}/confirm`. A manual-entry fallback saves a
confirmed profile through `PUT /api/v1/me/confirmed-profile`. Set
`VALIDATION_LOW_CONFIDENCE_THRESHOLD` to configure the confidence warning
threshold (from 0 through 1). The 80C comparison uses only a limit marked
verified, source-linked, and effective-dated in the selected tax rules; otherwise
the API reports that the limit could not be checked rather than guessing.

Confirmed profiles require decimal amounts as strings and explicit consent.
The employee/business-freelancer distinction is collected, but business-specific
tax treatment is not implemented. Confirming a profile does not calculate or
file tax.
