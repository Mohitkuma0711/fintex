---
applyTo: "frontend/**"
---

# Frontend instructions

- Use React function components, TypeScript, and the existing Vite setup.
- Keep route/page composition separate from reusable UI components and feature
  logic.
- Validate untrusted form and API data; never represent frontend calculations as
  authoritative tax results.
- Provide accessible labels, keyboard behavior, and responsive layouts.
- Never put secrets or sensitive taxpayer data in client-side source or logs.
- Run `npm run lint` and `npm run build` after frontend changes.
