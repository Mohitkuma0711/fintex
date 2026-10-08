# ADR 0002: Deterministic tax calculations

- **Status:** Accepted
- **Decision:** Tax calculations are performed only by a deterministic Python
  rules engine. LLMs may assist with extraction or language generation but
  never determine tax amounts.
- **Rationale:** Reproducibility, auditability, and traceable explanations are
  required for a tax product.
- **Consequences:** Versioned rules are maintained as data in
  `backend/app/rules/`; each calculation must retain a step trace and explain
  every reported number.
