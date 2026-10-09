# Security and privacy controls

This document describes implemented controls and the production work that is
still required. The application handles highly sensitive tax and identity
information; a passing test or dependency scan is not a security certification.

## Implemented controls

- Authentication is delegated to Supabase Auth. The API verifies JWT issuer,
  audience, expiry, subject, role, and signing algorithm.
- User-owned database queries are scoped to the authenticated user.
- Uploaded PDF, JPG, and PNG files are checked by size, MIME type, extension,
  and file signature, and are stored under a per-user path in a private bucket.
- Document access uses short-lived signed URLs. The default expiry is 300
  seconds and the accepted configuration range is 60–900 seconds.
- API requests include a request ID and security response headers. Production
  CORS requires an explicit HTTPS origin allowlist.
- PAN values are masked in user-facing extraction responses and redacted from
  structured logs. Request bodies, authorization headers, cookies, and user
  identity are removed from Sentry events.
- The browser's offline fallback is an in-memory cache scoped to the open
  session. It is cleared when the authenticated account changes or signs out;
  it is not written to local storage or IndexedDB.
- The 30-day document-retention option is backed by a scheduled cleanup
  command and a Render cron blueprint. It is only active after that cron is
  provisioned and configured successfully.
- User data deletion is authenticated and requires explicit `"DELETE"`
  confirmation. It attempts to remove storage objects, the Supabase Auth
  identity, and the associated database records.

## Required production safeguards

1. Configure the Render secrets and the exact frontend origin in
   `CORS_ORIGINS`. Never use `*` with credentials.
2. Use distinct Supabase projects and credentials for development, CI, and
   production. Keep the service-role key exclusively in backend secret
   storage; never use it in Vite variables.
3. Configure a real malware-scanning provider before accepting production
   uploads. The current `not_scanned` status is a placeholder, not a clean
   bill of health.
4. Verify that the private bucket's policies and object lifecycle match the
   application. Test signed-URL expiry and cross-account access after every
   storage-policy change.
5. Verify account deletion with failure injection. Storage, Supabase Auth, and
   PostgreSQL do not share a transaction: a provider outage can leave partial
   deletion that requires a retry or operator follow-up. Do not promise
   atomic deletion until retry/reconciliation behavior is implemented.
6. Provision and monitor the daily retention cron. A user's 30-day choice is
   not enforceable if the cron is absent or failing.
7. Keep Sentry's PII collection disabled, review scrubbing when adding new
   telemetry, and configure retention/access controls in the Sentry project.
8. Apply database backups, least-privilege access, encryption at rest, TLS,
   secret rotation, incident response, and account/data-deletion monitoring
   through the selected hosting providers.
9. Complete the official-source tax-rule verification and RAG ingestion
   before enabling real calculations or factual tax answers. The current
   placeholder tax rules deliberately fail closed.

## Audits

Run these from the repository root after dependency changes:

```bash
cd frontend
npm audit --omit=dev

cd ../backend
uvx --from=pip-audit pip-audit --locked pyproject.toml
```

GitHub Actions runs these checks alongside lint, tests, build, and the mocked
browser journey. The audit only covers known dependency advisories; it does not
replace application review, secret scanning, penetration testing, or provider
configuration review. No live production deployment or provider configuration
has been verified in this repository.
