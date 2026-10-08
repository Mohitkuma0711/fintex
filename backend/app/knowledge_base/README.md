# Official knowledge-base source pack

This directory is for **official, public source material only**. Do not put
taxpayer documents, credentials, private advice, or unverified summaries here.
The index is generated locally and is ignored by Git.

## Download exactly these source sets for each supported financial year

Download the source document and preserve its official URL and effective date.
Use the version applicable to the year in question; do not assume the latest
publication applies retrospectively.

1. **Income-tax Act, 2025 — consolidated Act, all chapters, sections, and
   Schedules**, plus its official commencement notification and any official
   corrigendum/amendment published for the selected financial year. Start from
   the Income Tax Department Acts landing page:
   <https://www.incometax.gov.in/iec/foportal/help/acts>.
2. **Income-tax Rules applicable to the Income-tax Act, 2025**, including
   schedules, forms, notified amendments, and commencement/effective-date
   notifications for the selected financial year. Download from the
   Department's official rules and notifications pages:
   <https://www.incometax.gov.in/iec/foportal/help/rules> and
   <https://www.incometax.gov.in/iec/foportal/communications/notifications>.
3. **Finance Act applicable to the selected financial year**, including the
   enacted Act, official Memorandum explaining the Finance Bill, and any
   corrigendum or commencement notice relevant to individual-tax provisions.
   Find enacted legislation and related publications from:
   <https://www.incometax.gov.in/iec/foportal/help/acts>.
4. **CBDT's official circular/instruction on deduction of tax from salaries
   under section 192 for the selected financial year**, with any corrigenda or
   replacement circulars. Use the CBDT circulars and instructions index:
   <https://www.incometax.gov.in/iec/foportal/communications/circulars>.
5. **CBDT circulars and notifications that interpret or administer the
   individual provisions in the downloaded Act/Rules/Finance Act** (for
   example, salary, withholding, deductions, exemptions, rebate, and return
   procedure). Include only publications identified as applicable to the
   selected year; record the exact circular/notification number, date, and
   affected provision in the document metadata. Use the same official CBDT
   circulars and notifications indexes linked above.
6. **Income Tax Department official FAQs and user guides** for the selected
   year covering the new and old tax regimes, salary/Form 16, deductions and
   exemptions, rebate, TDS, and individual income-tax return filing. Use the
   Department's official help/FAQ and e-filing help pages:
   <https://www.incometax.gov.in/iec/foportal/help> and
   <https://www.incometax.gov.in/iec/foportal/help/individual>.

These are the complete source categories this prototype is intended to ingest.
Do not substitute blogs, commercial tax sites, search-result snippets, social
posts, or generated explanations. Before downloading, confirm that each
landing-page path still resolves and that the document is published by the
Income Tax Department, CBDT, or the official Gazette. If an official URL moves,
record the replacement canonical URL rather than silently using a third-party
mirror. The FAQ topic list is a collection checklist, not a claim that every
FAQ currently exists as one document.

## Ingestion file layout

Place documents below `official/` as PDF, HTML, or Markdown. For each source
file, provide a sibling metadata file named `<filename>.<ext>.metadata.json`,
for example `act-2025.pdf.metadata.json`:

```json
{
  "source": "Income-tax Act, 2025 (consolidated text)",
  "url": "https://www.incometax.gov.in/iec/foportal/help/acts",
  "effective_date": "2026-04-01"
}
```

Use the direct document URL in `url` whenever the official publisher provides
one. `effective_date` is the date the legal text or guidance takes effect, not
the date it was downloaded. The ingester rejects non-official hosts and
metadata omissions. Section/chapter headings are extracted from the document
and stored per chunk; review the generated citations before deployment.

## Build and query the index

Configure `GOOGLE_API_KEY` in the backend environment, add the source pack, and
run:

```bash
cd backend
uv run python -m app.services.rag.ingest
```

The FAISS index and its metadata are written under `knowledge_base/.index/`.
They are local build artifacts: keep source documents and metadata in version
control only when their redistribution terms permit it; otherwise provision
them securely during deployment. Rebuild the index whenever source documents,
URLs, sections, or effective dates change.

At runtime, retrieval uses cosine similarity and a configured minimum score.
When the index is absent, unavailable, or yields no relevant passage, chat must
say it is unsure and must not answer from model memory.
