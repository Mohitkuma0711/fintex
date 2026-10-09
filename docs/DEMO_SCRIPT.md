# FinTax AI — 3-minute demo walkthrough

## Important demo boundary

The checked-in tax rules are deliberately incomplete placeholders. Do not
present a calculated tax amount, a regime recommendation, or a savings figure
as real. Calculate, Compare, Simulator, and tax-impact suggestions fail closed
until the rules are verified and versioned. The browser journey in CI mocks API
responses only and is not evidence of tax correctness.

For an honest product walkthrough, use a synthetic-only Supabase account and
the seeded document below. Explain the calculation gate instead of showing
invented results. A complete judging demo that includes tax outputs requires
verified rules and an official-source knowledge base before the event.

## Setup

1. Configure Supabase, PostgreSQL, API, and frontend environments using
   [deployment.md](./deployment.md).
2. Create a dedicated synthetic demo identity in Supabase Auth. Apply the
   migrations, then set `DEMO_USER_ID` to that identity's UUID and optionally
   `DEMO_USER_EMAIL` to its synthetic email.
3. From `backend/`, run `uv run python -m app.maintenance.seed_demo`. It
   uploads a visibly synthetic, non-valid PDF and stores synthetic extraction
   fields; it does not create tax calculations or suggestion results.
4. Sign in at `/login`, then open the `/review?documentId=<printed-id>` path
   from the seeder. Use no real taxpayer data.

## Walkthrough (3 minutes)

| Time | Screen and narration |
| --- | --- |
| 0:00–0:25 | **Problem and trust boundary.** Introduce the Indian tax-planning workflow. State that Gemini extracts or explains text but never performs tax arithmetic; the deterministic rules engine owns every tax number. |
| 0:25–0:55 | **Upload and extract.** Show the clearly marked synthetic document and the extraction status. Point out that unknown fields remain blank and extracted values include confidence and source page. |
| 0:55–1:20 | **Verify.** Open the seeded review path. Show editable extracted fields, validation status, consent, and the guidance-not-professional-advice notice. Do not enter real PAN or salary details. |
| 1:20–1:50 | **Calculate.** Open Dashboard. In this repository state, show the rules-not-ready state and explain that the system refuses to guess rather than displaying fabricated comparisons. After rules have been officially verified, this is where old/new regime traces and the exact comparison belong. |
| 1:50–2:15 | **Suggest.** Show the suggestions surface and explain that every impact is intended to be calculated by rerunning the same deterministic engine. Do not claim savings while rules are placeholders. |
| 2:15–2:45 | **Explain.** Show Chat and the official-source citation UI. The current RAG knowledge base must be ingested with approved source documents before presenting factual answers as grounded. |
| 2:45–3:00 | **Close.** Show Report / filing guidance and reiterate that the product prepares guidance and a summary; it does not submit an income-tax return or replace professional advice. |

## Offline behavior

Previously successful GET responses and the latest generated PDF can be reused
from memory for the lifetime of the open browser session if a later request
fails. The UI marks that state as cached/offline and warns that changes are not
saved. Cache contents are not persisted across reloads and are cleared on
sign-out or account switch. A first-time offline visit, uploads, writes, and a
new chat stream still require connectivity.

## Current known gaps

- Tax rules and official-source RAG content are not production-ready.
- Virus scanning is a placeholder.
- The full browser test uses mocked APIs and a synthetic user; it is not an
  end-to-end test against deployed Supabase, Gemini, or a production database.
- No live frontend/backend deployment has been verified.
