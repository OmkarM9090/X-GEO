# X-GEO — Frontend (Phase 1)

Explainable Generative Engine Optimization & Verification Suite. Phase 1 ships the complete,
production-grade frontend scaffolding: marketing site, authentication, dashboard shell, and a
dual-theme design system. All data is mocked via typed fixtures in `src/lib/mock-data.ts`.

## Stack

| Area | Choice |
| --- | --- |
| Framework | Vite + React 19 + TypeScript (strict) |
| Styling | Tailwind CSS (v4 engine via `@tailwindcss/vite`) + CSS variable tokens in `src/styles/tokens.css`, mapped through `tailwind.config.ts` |
| UI primitives | shadcn-style components (Radix primitives, hand-built in `src/components/ui`) |
| Animation | GSAP 3.13 (`ScrollTrigger`, `SplitText`, `Flip`) + `@gsap/react` |
| Smooth scroll | Lenis, wired into the GSAP ticker |
| State | Zustand (theme, UI) + TanStack Query (prepared for Phase 2 API) |
| Routing | React Router v6 |
| Forms | React Hook Form + Zod |
| Charts | Recharts + bespoke animated SVG |
| Fonts | Geist (headings/UI), Inter (body), Geist Mono (code/metrics) |

## Getting started

```bash
pnpm install
pnpm dev        # local dev server
pnpm build      # production build → dist/
pnpm preview    # serve the production build
```

## Routes

- `/` landing (11 animated sections incl. scroll-scrubbed Monte Carlo CPI demo)
- `/features`, `/pricing`, `/docs`
- `/signin`, `/signup`, `/forgot-password` (RHF + Zod, mocked 1.5 s submits)
- `/dashboard` → overview (animated metrics, audits table, trend chart, empty-state toggle),
  `/dashboard/projects`, `/dashboard/audits`, `/dashboard/optimizations`,
  `/dashboard/reports`, `/dashboard/settings` (shells with Phase 2 badges)

## Conventions

- **Theming** — dark mode is the default; preference persists under `localStorage["xgeo-theme"]`
  and is applied pre-paint by an inline script in `index.html`. All colors are HSL channel
  variables consumed as `hsl(var(--token) / <alpha-value>)`.
- **Animation** — every GSAP effect is wrapped in `gsap.matchMedia()` and gated on
  `(prefers-reduced-motion: no-preference)`; reduced-motion users always see the final state.
  Layout properties are never animated (transform/opacity only).
- **Mock data** — typed fixtures live in `src/lib/mock-data.ts`; swap with TanStack Query
  hooks in Phase 2 without touching components.
- **Import alias** — `@/` maps to `src/`.
