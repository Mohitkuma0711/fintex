# FinTax AI frontend

Vite + React + TypeScript client styled with Tailwind CSS, bundled Space Grotesk
and Manrope fonts, and shadcn/ui conventions. The application shell includes
light/dark themes, accessible responsive navigation, page transitions, motion
primitives, and landing-page previews. Tax-workflow routes remain placeholders;
the frontend does not calculate tax.

The theme and Tailwind design tokens live in `src/index.css`. Shared motion,
layout, and UI components live in `src/components/`; application-wide providers
live in `src/providers/`. The 3D landing scene is lazy-loaded on capable desktop
devices and falls back to static artwork for mobile, low-power, or
reduced-motion contexts.

```bash
npm install
npm run dev
```

Use `npm run lint` and `npm run build` to validate frontend changes. Shared UI
primitives follow the shadcn/ui component conventions in `src/components/ui`.

Copy `.env.example` to `.env.local` and add the Supabase project URL and public
anon key to enable email/password signup and login. Private workflow routes
redirect to `/login`; a successful Supabase session is attached as a bearer
token to API requests. Tax data contracts and authenticated requests are in
`src/lib/api.ts`.
