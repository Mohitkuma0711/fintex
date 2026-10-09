# Deployment and environment setup

Deployment is configured but not performed by this repository. A live release
requires GitHub Actions secrets, Vercel and Render projects, a production
Supabase project, a PostgreSQL database, verified tax-rule data, and official
RAG sources.

## Frontend on Vercel

1. Create a Vercel project rooted at `frontend/`, using the Vite framework
   preset and `npm run build` / `dist`.
2. Configure `VITE_API_BASE_URL`, `VITE_SUPABASE_URL`,
   `VITE_SUPABASE_ANON_KEY`, and optionally `VITE_SENTRY_DSN` as Vercel
   production environment variables.
3. Add GitHub repository secret `VERCEL_TOKEN` and repository variables
   `VERCEL_ORG_ID` and `VERCEL_PROJECT_ID`.
4. The `deploy-frontend` job in `.github/workflows/ci.yml` deploys `main` only
   after CI passes. If these values are missing, the job reports a skip rather
   than claiming deployment.

The Vercel configuration includes SPA route rewrites and baseline security
headers. Restrict the project to the intended domains and verify those headers
on the deployed response.

## Backend on Render

1. Create a Render Blueprint from `render.yaml`, or create an equivalent Docker
   web service rooted at `backend/` with health check `/api/v1/health`.
2. Create PostgreSQL and a private Supabase Storage bucket. Run Alembic
   migrations against the production database before serving user traffic.
3. Set every `sync: false` environment value in the Render dashboard. See the
   backend and frontend `.env.example` files for the full local configuration.
4. Configure `CORS_ORIGINS` as a JSON array containing only the production
   HTTPS frontend origin, for example `["https://app.example.com"]`.
5. Create a Render deploy hook and set it as GitHub secret
   `RENDER_DEPLOY_HOOK_URL`. The GitHub deployment job triggers it after the
   backend and frontend CI jobs pass. Keep Render's direct auto-deploy disabled
   so an untested push cannot bypass CI.
6. Provision the cron service in `render.yaml`, provide the same database and
   Supabase storage credentials, and verify that its daily run removes expired
   objects and metadata.

`DATABASE_URL`, Supabase keys, `GOOGLE_API_KEY`, and Sentry DSNs are secrets.
Never expose backend secrets through `VITE_*` variables or commit `.env` files.
The Gemini key and Sentry DSNs are optional for boot but required for their
respective integrations. Set `TAX_RULES_FILE` only to a complete reviewed
ruleset; do not remove the fail-closed behavior to make a demo appear
successful.

## Health and post-deploy checks

- `GET /api/v1/health` is the Render liveness check; it does not currently prove
  database, Supabase, Gemini, or tax-rule readiness.
- Check `/docs` only if public OpenAPI access is acceptable for the environment.
- Sign in with a synthetic account, verify private upload and signed URL
  expiry, confirm that API CORS allows only the production origin, and test
  account deletion and the 30-day retention process.
- The checked-in tax rules still contain TODO values and no production
  deployment URLs or credentials were supplied. Tax compute/suggestions and
  complete production readiness therefore remain unverified.
