# Implementation Plan: My Tax Documents & Smart Tax-Saving Engine

**Date**: 2026-10-10 | **Spec**: User-supplied master prompt

## Summary

Extend the existing React/Vite + FastAPI FinTax application in phases. Preserve authentication,
private storage, review, deterministic tax calculation, verified-rule gating, regime comparison,
simulator, and chat. The first executable increment is the hackathon-critical document-vault and
tax-saving-advisor experience. Gemini remains an extraction/explanation provider only; it never
calculates tax, establishes legal eligibility, or writes final amounts.

## Technical Context

**Language/Version**: Python 3.12 backend; React + TypeScript frontend  
**Primary Dependencies**: FastAPI, async SQLAlchemy, Pydantic, React Query, React Hook Form, Vite, Google GenAI SDK  
**Storage**: Existing authenticated user-scoped local/Supabase document storage and database repositories  
**Testing**: pytest, Ruff, frontend production build, Playwright browser smoke tests  
**Target Platform**: Local hackathon demo first; deployable backend/frontend later  
**Constraints**: Official-source rules only; fail closed for unverified rules; no fabricated extraction; no secrets in frontend or logs; no guaranteed savings claims  

## Constitution Check

- Deterministic calculations remain authoritative: **PASS**
- Verified legal rules and official citations are required: **PASS**
- Uploaded documents are untrusted and user-scoped: **PASS**
- Missing, conflicting, or low-confidence data is surfaced for review: **PASS**
- Gemini is not treated as legal or calculation authority: **PASS**
- Existing authentication, storage, and workflows are preserved: **PASS**

## Applied Guidelines

- Existing extraction strategy and typed `ExtractionError` codes are reused.
- Existing `require_ready()` and `require_suggestion_terms_ready()` gates remain mandatory.
- Existing repository/service/router separation is extended instead of bypassed.
- Existing React Query caching, protected routes, and accessible status/error patterns are reused.

## Implementation Steps

### Step 1: [Cross-cutting] Establish the requirements and acceptance baseline
- **Requirements**: REQ-001, REQ-002, REQ-003, REQ-004, REQ-005, REQ-006, REQ-007, REQ-008, REQ-009, REQ-010, REQ-011, REQ-012
- **Description**: Treat this document as the source of truth for phased delivery. Define acceptance evidence for security, extraction, tax calculation, recommendations, rules transparency, and browser journeys.

### Step 2: [Cross-cutting] Strengthen the document domain and vault metadata
- **Requirements**: REQ-001, REQ-002, REQ-003, REQ-011
- **Description**: Add document category, financial year, assessment year, processing state, verification state, tax relevance, missing-information metadata, replacement, deletion, download, search, and filtering while preserving user ownership and private storage.

### Step 3: [Cross-cutting] Harden extraction and review provenance
- **Requirements**: REQ-004, REQ-005, REQ-006, REQ-011
- **Description**: Keep Gemini behind the backend; validate structured output; support deterministic text-PDF recovery; preserve source page, confidence, masking, warnings, contradictions, user correction, consent, and explicit review-required states.

### Step 4: [Cross-cutting] Build the AI Tax-Saving Advisor
- **Requirements**: REQ-007, REQ-008, REQ-009, REQ-010, REQ-012
- **Description**: Add a protected advisor route using deterministic suggestions. Group results as potentially eligible, more information needed, and not eligible/unavailable. Every result must include section, year, conditions, evidence, missing facts, limits, estimated amount, old/new impact, official source, confidence, risks, and next action.

### Step 5: [Cross-cutting] Expand verified rules and legal-source transparency
- **Requirements**: REQ-007, REQ-008, REQ-009, REQ-010
- **Description**: Version rules by FY/AY and effective dates. Add a legal sources view showing governing act, verified timestamp, source URLs, regime applicability, and deliberately blocked provisions. Unverified or stale rules remain excluded from calculations.

### Step 6: [Cross-cutting] Complete regime comparison and audit traces
- **Requirements**: REQ-008, REQ-009, REQ-010
- **Description**: Ensure both regimes show income heads, exemptions, deductions, taxable income, rebate, surcharge, cess, TDS, final liability/refund, assumptions, and a linked calculation trace. Savings must be before-tax minus after-tax under identical facts.

### Step 7: [Cross-cutting] Add chat grounding and privacy controls
- **Requirements**: REQ-004, REQ-007, REQ-010, REQ-011
- **Description**: Ground chat answers in confirmed profile facts, extracted fields, recommendation IDs, rules, and official URLs. Distinguish facts from assumptions, ask for missing data, never claim filing or government verification, and redact sensitive identifiers in logs.

### Step 8: [Cross-cutting] Validate the complete product
- **Requirements**: REQ-001 through REQ-012
- **Description**: Add unit, API, integration, browser, authorization, malformed-document, duplicate/conflict, expired-rule, and recommendation-savings tests. Run focused checks after each phase and full validation before sign-off.

## Project Structure

```text
backend/app/
  api/v1/routes/documents.py
  api/v1/routes/tax.py
  models/
  repositories/documents.py
  services/documents.py
  services/extraction/
  services/suggestions/
  services/tax_engine/
  rules/
  schemas/
backend/tests/
  unit/
  integration/
frontend/src/
  app/App.tsx
  components/layout/AppShell.tsx
  lib/api.ts
  pages/UploadPage.tsx
  pages/ReviewPage.tsx
  pages/TaxAdvisorPage.tsx
  pages/RulesPage.tsx
  pages/DocumentsPage.tsx
.github/modernize/master-tax-platform/
  plan.md
  checkpoints/spec-to-plan.yaml
  checkpoints/plan-to-tasks.yaml
```

## Testing Strategy

- **appType**: Mixed FastAPI API + React SPA
- **Critical user journeys**:
  1. Upload a valid text PDF, recover from Gemini throttling, review and correct values.
  2. List, filter, replace, download, and delete only the signed-in user's documents.
  3. Compare old/new regimes and inspect the deterministic calculation trace.
  4. View advisor groups with rupee savings, evidence, citations, and blocked unsupported areas.
  5. Open legal sources and verify the active FY/AY rules and source links.
- **primaryValidationStack**: pytest + Ruff + Vite build + Playwright browser validation
- **fallbackMatrix**:
  - `infra-tier`: local storage/SQLite-compatible test fixtures when Supabase is unavailable; gap: hosted storage policy behavior
  - `browser-tier`: shared browser smoke tests; fallback: API integration tests; gap: visual regression coverage
- **Environment requirements**: Python virtual environment, Node/npm, running FastAPI and Vite servers, synthetic fixtures only
- **knownGaps**: Real Gemini provider availability, production Supabase policies, full legal review of future rules, and unimplemented non-salary document categories until their schemas and verified rules exist
- **Test data strategy**: synthetic documents, isolated user IDs, explicit cleanup, no real taxpayer records
- **Acceptance criteria**: no cross-user access, no unverified calculation, no fabricated extraction, every recommendation has evidence/citation metadata, and all critical browser journeys pass
- **Validation review expectations**: reviewer confirms rule version, source URL, calculation trace, extraction provenance, error state, privacy boundary, and unsupported-area messaging

## Tasks

### Phase 1 — Setup and baseline
- [ ] T001 [Plan:1.1] Record the supplied master prompt and acceptance criteria in `.github/modernize/master-tax-platform/plan.md`.
- [ ] T002 [P] [Plan:1.1] Inventory existing document, extraction, tax, suggestion, chat, navigation, and test entry points in the repository.
- [ ] T003 [P] [Plan:1.1] Capture baseline backend tests, Ruff, frontend build, health check, and browser smoke evidence.

### Phase 2 — Foundational document vault
- [ ] T004 [Plan:2.1] Extend document schemas and models with category, FY/AY, verification state, tax relevance, warnings, and missing-information metadata in `backend/app/schemas` and `backend/app/models`.
- [ ] T005 [Plan:2.1] Extend document repository/service APIs for list filtering, replacement, deletion, and signed download in `backend/app/repositories/documents.py` and `backend/app/services/documents.py`.
- [ ] T006 [P] [Plan:2.1] Add authenticated document endpoints and response contracts in `backend/app/api/v1/routes/documents.py`.
- [ ] T007 [P] [Plan:2.1] Build `DocumentsPage.tsx` with drag-and-drop multi-file upload, previews, categories, search, filters, statuses, replacement, deletion, and download.
- [ ] T008 [Plan:2.1] Add database migration and synthetic fixture coverage for document ownership, duplicate handling, retention, and status transitions.

### Phase 3 — Extraction and review
- [ ] T009 [Plan:3.1] Extend extraction schemas for source references, warnings, conflicts, and document-specific fields while preserving strict Pydantic validation.
- [ ] T010 [Plan:3.1] Update `backend/app/services/extraction/orchestrator.py` and jobs to preserve deterministic fallback, confidence, source pages, typed errors, and review-required status.
- [ ] T011 [P] [Plan:3.1] Update `ReviewPage.tsx` to distinguish AI-extracted, verified, and user-corrected values and show missing/conflicting evidence.
- [ ] T012 [Plan:3.1] Add extraction tests for malformed JSON, rate limiting, low confidence, wrong FY/AY, conflicting values, and user correction.

### Phase 4 — Advisor and recommendations
- [ ] T013 [Plan:4.1] Add advisor response schemas and grouped recommendation contracts in `backend/app/schemas`.
- [ ] T014 [Plan:4.1] Extend `backend/app/services/suggestions/engine.py` to emit evidence, missing facts, regime impact, limits, savings trace, confidence, risks, and next action.
- [ ] T015 [Plan:4.1] Add `/tax/advisor` or equivalent protected route using existing deterministic services in `backend/app/api/v1/routes/tax.py`.
- [ ] T016 [P] [Plan:4.1] Create protected `TaxAdvisorPage.tsx` with potentially eligible, more information needed, and unavailable groups.
- [ ] T017 [Plan:4.1] Add browser and API tests proving Gemini cannot override tax numbers or create unsupported recommendations.

### Phase 5 — Rules and legal sources
- [ ] T018 [Plan:5.1] Add rule metadata and source-index schemas for rule ID, act, section, effective dates, regime, FY/AY, verification status, and reviewer notes.
- [ ] T019 [Plan:5.1] Add a rules-summary/legal-sources endpoint and connect `RulesPage.tsx` to the active verified ruleset.
- [ ] T020 [Plan:5.1] Add explicit blocked-until-verified records for capital gains, late filing, business/vehicle treatment, unsupported deductions, and ambiguous property cases.
- [ ] T021 [Plan:5.1] Add tests for stale, missing-source, conflicting, and unverified rules failing closed.

### Phase 6 — Comparison, chat, and dashboard integration
- [ ] T022 [Plan:6.1] Complete side-by-side regime output and calculation trace coverage in `backend/app/services/tax.py` and `backend/app/api/v1/routes/tax.py`.
- [ ] T023 [Plan:7.1] Ground chat responses in confirmed facts, recommendation IDs, rule citations, and explicit assumptions in `backend/app/services/chat/service.py`.
- [ ] T024 [P] [Plan:6.1,7.1] Integrate document counts, missing evidence, verified suggestions, tax estimates, and rules timestamp into `DashboardPage.tsx`.

### Phase 7 — Final validation and documentation
- [ ] T025 [Plan:8.1] Add end-to-end browser coverage for upload, extraction fallback, review, vault management, advisor, simulator, rules, and chat.
- [ ] T026 [P] [Plan:8.1] Update `.env.example`, setup, deployment, troubleshooting, retention, and legal limitation documentation.
- [ ] T027 [Plan:8.1] Run full backend tests, Ruff, frontend build, health checks, browser tests, and document unresolved legal/provider limitations.

## Requirement Mapping

| REQ ID | Description | Plan Items | Implementation Evidence |
|--------|-------------|------------|------------------------|
| REQ-001 | Secure multi-document upload and private storage | 2.1, 8.1 | document routes/services, DocumentsPage, ownership tests |
| REQ-002 | Document organization, search, filtering, replacement, deletion, download | 2.1 | document repository/routes, DocumentsPage |
| REQ-003 | Processing, verification, archive, missing-data statuses | 2.1, 3.1 | schemas/models, job state transitions, UI status badges |
| REQ-004 | Secure Gemini extraction with schema validation and provenance | 3.1, 7.1 | extraction orchestrator, schemas, typed errors, chat grounding |
| REQ-005 | Review, correction, consent, and confidence handling | 3.1 | ReviewPage, validation and correction tests |
| REQ-006 | Decimal-safe deterministic tax calculations | 6.1 | tax services, calculation traces, formula tests |
| REQ-007 | Personalized lawful recommendations | 4.1, 7.1 | suggestion engine, advisor route/page, grounded chat |
| REQ-008 | Official versioned legal rules and source links | 5.1 | rules metadata, rules-summary endpoint, RulesPage |
| REQ-009 | Old/new regime comparison and action savings | 4.1, 6.1 | tax routes/services, simulator, recommendation traces |
| REQ-010 | Explainable evidence, risks, limits, next actions, and blocked areas | 4.1, 5.1, 7.1 | advisor groups, blocked list, citations, chat |
| REQ-011 | Privacy, authorization, retention, masking, and auditability | 2.1, 3.1, 8.1 | user-scoped APIs, storage, masking, security tests |
| REQ-012 | Automated unit, integration, browser, and security validation | 1.1, 4.1, 5.1, 8.1 | backend tests, browser journeys, final validation report |
