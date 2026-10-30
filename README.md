# X-GEO

Explainable Generative Engine Optimization and Verification Suite: a B2B SaaS platform that
audits how visible and citable a website is inside AI answer engines (ChatGPT, Perplexity,
Google AI Overviews) and tracks the prompts that matter to its buyers.

The repository contains two applications:

| Path | What it is |
| --- | --- |
| `frontend/` | React 19 + TypeScript + Vite marketing site and dashboard shell |
| `backend/` | FastAPI + PostgreSQL/pgvector + Celery API, crawler and scoring engine |

## Quick start (Docker)

```bash
make up          # postgres+pgvector, redis, backend, celery worker/beat, frontend
make migrate     # apply database migrations (AUTO_CREATE_TABLES also covers dev)
make seed        # optional: demo tenant, project, audit and embedded chunks
```

| Service | URL |
| --- | --- |
| API | http://localhost:8000/api/v1/health |
| API docs (Swagger) | http://localhost:8000/api/docs |
| API docs (ReDoc) | http://localhost:8000/api/redoc |
| Frontend | http://localhost:5173 |

## Quick start (no Docker)

The backend ships a Docker-free development path built on the `pgserver` wheel
(PostgreSQL 16 + pgvector) so migrations and the full test suite run anywhere:

```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt -r requirements-dev.txt
.venv/bin/python scripts/dev_db.py start      # starts PostgreSQL on a unix socket, creates both DBs
.venv/bin/alembic upgrade head
.venv/bin/python scripts/seed_db.py
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

From the repository root the same flows are available as `make dev-db` and `make local-test`.

## Backend

### Architecture

Repository–Service–Controller, enforced by convention and review:

```
app/api/          FastAPI routers + dependencies (HTTP only, never SQL)
app/schemas/      Pydantic request/response models (no ORM types)
app/services/     all business logic (audits, PCS scoring, crawl orchestration, chunks)
app/repositories/ all SQLAlchemy queries (one repository per aggregate)
app/models/       pure SQLAlchemy 2.0 mappings (no business methods)
app/crawler/      Scrapy / httpx / Playwright fetchers, robots policy, clean + extract pipelines
app/tasks/        Celery application and crawl/simulation tasks
app/core/         config, database, security (SSRF, JWT, scrypt), middleware, logging, errors
app/db, app/workers  stable import surfaces for infrastructure callers
```

### What it does today

- **Projects & audits** — CRUD scoped to the authenticated tenant, credit consumption per audit,
  target URLs validated against the project domain.
- **Crawling** — robots.txt policy, SSRF protection with DNS pinning, redirect re-validation,
  Scrapy primary transport with httpx fallback, SPA detection with a Playwright (Chromium) escalation path.
- **Scoring** — Technical readiness, Semantic alignment, Evidentiary density and Machine
  readability combined into the Prompt Citation Score, with a full explainability breakdown
  persisted per audit (`score_breakdown`).
- **Chunks & retrieval** — markdown chunking (256 tokens / 32 overlap), pgvector embeddings,
  generated `tsvector`, reciprocal-rank fusion of vector + full-text search, alignment scoring
  against tracked prompts.
- **Auth** — Supabase JWTs verified locally (JWKS or shared secret), JIT shadow-row provisioning,
  scrypt password hashing for local accounts, `POST /api/v1/auth/dev-token` for local development.

### Security posture

- Every outbound URL passes `validate_url` + `check_ssrf` (private, loopback, link-local,
  CGNAT and cloud-metadata ranges are blocked; port allow-list; optional DNS pinning).
- Crawled content is sanitised before storage and before it can reach an LLM prompt.
- Rate limiting (in-process or Redis-backed), request ids, structured JSON logs in containers.
- `APP_ENV`-aware configuration validator: staging/production refuse debug mode, dev tokens,
  wildcard CORS and placeholder Supabase credentials.

### Tests

```bash
cd backend
.venv/bin/python -m pytest                     # unit + integration + e2e (needs a database)
.venv/bin/python -m pytest tests/unit -q       # no database required
XGEO_REQUIRE_DB=1 .venv/bin/python -m pytest   # CI mode: missing database fails instead of skipping
```

The suite covers URL validation, SSRF prevention, HTML cleaning, chunking, PCS scoring,
security helpers, health probes, auth flows, projects/audits APIs, repositories, chunk search
and a full crawl→score→search pipeline against an in-process HTTP fixture server.

### Quality gates

```bash
cd backend
.venv/bin/ruff check app tests migrations scripts
.venv/bin/black --check app tests scripts migrations
.venv/bin/isort --check-only app tests migrations scripts
.venv/bin/mypy app
```

## Frontend

```bash
cd frontend
npm install
npm run dev
npm run typecheck
npm run build
```

The Vite dev server binds to `0.0.0.0` for Arena previews. Production output is generated in `frontend/dist/`.

### Stack

- React 19, TypeScript, Vite, React Router v6
- Tailwind CSS v4 with shared CSS-variable design tokens
- GSAP 3 + `@gsap/react` + ScrollTrigger / SplitText
- Lenis smooth scrolling, disabled for touch-first and reduced-motion preferences
- TanStack Query, Zustand, React Hook Form + Zod
- Recharts and typed mock fixtures
- Locally hosted Geist Variable and Geist Mono fonts (OFL license in `frontend/public/fonts/`)

### Routes

- `/`, `/features`, `/pricing`, `/changelog`, `/docs`
- `/signin`, `/signup`, `/forgot-password`
- `/dashboard`, `/dashboard/projects`, `/dashboard/audits`, `/dashboard/optimizations`, `/dashboard/reports`, `/dashboard/settings`

### Architecture

Application bootstrap and providers live under `frontend/src/app/`; route pages are separated by marketing, auth, and dashboard domains. Reusable UI primitives, product components, shared components, and GSAP animation building blocks have dedicated folders. Typed fixtures are in `frontend/src/data/`, domain types in `frontend/src/types/`, and API helpers in `frontend/src/lib/api.ts`.

All GSAP motion is scoped with `useGSAP`, cleaned up on unmount, and guarded by `prefers-reduced-motion`. Route changes refresh ScrollTrigger instances; window resize refreshes are debounced.

## Configuration

Copy `.env.example` to `.env` and `backend/.env.example` to `backend/.env` (`make env` does both).
Every variable has a safe development default; Supabase credentials become mandatory outside
development. See `backend/.env.example` for the annotated list.
