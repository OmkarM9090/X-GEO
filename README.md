# X-GEO

Explainable Generative Engine Optimization and Verification Suite. The repository is organized as a frontend-first workspace; the API service is planned for Step 2B.

## Frontend

```bash
cd frontend
npm install
npm run dev
npm run typecheck
npm run build
```

The Vite dev server binds to `0.0.0.0` for Arena previews. Production output is generated in `frontend/dist/`.

## Stack

- React 19, TypeScript, Vite, React Router v6
- Tailwind CSS v4 with shared CSS-variable design tokens
- GSAP 3 + `@gsap/react` + ScrollTrigger / SplitText
- Lenis smooth scrolling, disabled for touch-first and reduced-motion preferences
- TanStack Query, Zustand, React Hook Form + Zod
- Recharts and typed mock fixtures
- Locally hosted Geist Variable and Geist Mono fonts (OFL license in `frontend/public/fonts/`)

## Routes

- `/`, `/features`, `/pricing`, `/changelog`, `/docs`
- `/signin`, `/signup`, `/forgot-password`
- `/dashboard`, `/dashboard/projects`, `/dashboard/audits`, `/dashboard/optimizations`, `/dashboard/reports`, `/dashboard/settings`

## Architecture

Application bootstrap and providers live under `frontend/src/app/`; route pages are separated by marketing, auth, and dashboard domains. Reusable UI primitives, product components, shared components, and GSAP animation building blocks have dedicated folders. Typed fixtures are in `frontend/src/data/`, domain types in `frontend/src/types/`, and API helpers in `frontend/src/lib/api.ts`.

All GSAP motion is scoped with `useGSAP`, cleaned up on unmount, and guarded by `prefers-reduced-motion`. Route changes refresh ScrollTrigger instances; window resize refreshes are debounced.
