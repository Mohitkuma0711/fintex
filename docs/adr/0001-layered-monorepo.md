# ADR 0001: Layered monorepo

- **Status:** Accepted
- **Decision:** Keep the FastAPI backend and Vite frontend in one repository,
  with independent dependency manifests and clear application/data boundaries.
- **Rationale:** Hackathon contributors can work in one place while backend and
  frontend deployments remain independently buildable.
- **Consequences:** Shared API contracts should be documented and validated at
  the backend boundary; dependency and build commands are scoped by app.
