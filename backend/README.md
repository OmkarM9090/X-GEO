# X-GEO backend

FastAPI service for the X-GEO audit platform: multi-tenant projects, audits, the crawler,
chunk/embedding storage with hybrid retrieval, and the Prompt Citation Score.

## Layout

```
app/
  api/v1/        routers: health, auth, projects, audits, crawls
  api/deps.py    request-scoped dependency aliases (single import site for routes)
  core/          config, database, dependencies, security, middleware, logging, errors
  db/            stable re-export surface for session helpers (tasks, scripts)
  crawler/       fetchers (Scrapy/httpx/Playwright), robots policy, clean + extract pipelines
  models/        pure SQLAlchemy 2.0 mappings
  repositories/  every query lives here (BaseRepository + one per aggregate)
  schemas/       Pydantic request/response contracts
  services/      business logic: auth, projects, audits+PCS, crawl orchestration, chunks
  tasks/         Celery app, crawl tasks, simulation tasks
  workers/       Celery worker entrypoints (`celery -A app.workers`)
migrations/      Alembic (async env, autogenerate-friendly naming convention)
scripts/         dev_db.py (Docker-free PostgreSQL), seed_db.py, init.sql, create_migration.sh
tests/           unit / integration / e2e
```

## Local development

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt -r requirements-dev.txt

.venv/bin/python scripts/dev_db.py start        # PostgreSQL 16 + pgvector (unix socket)
.venv/bin/alembic upgrade head                  # schema
.venv/bin/python scripts/seed_db.py             # demo tenant + audit + chunks
.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

`scripts/dev_db.py` supports `start|stop|status|url`; `make dev-db` wraps `start`.
If you prefer Docker, `make up` runs the same stack with postgres, redis and Celery.

### Database-first workflow

```bash
.venv/bin/alembic revision --autogenerate -m "add x"   # or: make migration msg="add x"
.venv/bin/alembic upgrade head
.venv/bin/alembic check                                # detect model/migration drift
```

The initial migration also creates the `vector` and `pg_trgm` extensions. Extension creation
is idempotent, so `AUTO_CREATE_TABLES=true` and `alembic upgrade head` can both be used in
development.

### Celery

```bash
.venv/bin/celery -A app.tasks.celery_app:celery_app worker -Q xgeo.crawl,xgeo.simulation -l info
.venv/bin/celery -A app.tasks.celery_app:celery_app beat -l info
```

Set `TASK_ALWAYS_EAGER=true` to execute tasks inline (used by the test suite and the seed script).

## API surface

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/v1/health`, `/health/db`, `/health/ready` | liveness, database + pgvector, readiness |
| POST | `/api/v1/auth/signup`, `/signin`, `/refresh`, `/signout`, `/dev-token` | Supabase-backed auth (dev-token is DEBUG only) |
| GET | `/api/v1/auth/me` | current user, role and credits |
| GET/POST | `/api/v1/projects` | list / create projects |
| GET/PATCH/DELETE | `/api/v1/projects/{id}` | project detail (with counts), update, delete |
| POST | `/api/v1/audits` | create an audit (sync or queued) |
| GET | `/api/v1/audits`, `/api/v1/audits/{id}` | list / detail with scores and chunks |
| GET | `/api/v1/audits/{id}/scores`, `/api/v1/audits/{id}/chunks` | explainability + stored chunks |
| POST | `/api/v1/audits/{id}/search` | hybrid (vector + full-text) chunk search |
| POST | `/api/v1/crawls/trigger`, GET `/api/v1/crawls`, `/api/v1/crawls/{id}/status` | crawl jobs |

Interactive docs: `/api/docs` (Swagger), `/api/redoc`, schema at `/api/openapi.json`.

## Tests

```bash
.venv/bin/python -m pytest                  # everything (skips DB tests when no database is reachable)
.venv/bin/python -m pytest tests/unit -q    # pure logic, no database
XGEO_REQUIRE_DB=1 .venv/bin/python -m pytest
```

The harness pins test settings before importing the app, resolves the database from
`TEST_DATABASE_URL`/`XGEO_TEST_DATABASE_URL`, then Docker's `localhost:5432`, then the bundled
`pgserver` data directory, and bootstraps the schema with `create_all` plus the `vector` and
`pg_trgm` extensions.
