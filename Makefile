# =============================================================================
# X-GEO developer commands
# =============================================================================
.DEFAULT_GOAL := help
COMPOSE ?= docker compose
BACKEND  = $(COMPOSE) exec backend

# Prefer the project virtualenv for the Docker-free targets, then fall back to
# the system interpreter (Docker images have both on PATH).
VENV_PYTHON := $(CURDIR)/backend/.venv/bin/python
PYTHON ?= $(shell test -x $(VENV_PYTHON) && echo $(VENV_PYTHON) || echo python3)

.PHONY: help env up down logs logs-api logs-worker psql shell \
        migrate migration migrate-down seed \
        test test-unit test-integration test-e2e coverage \
        format lint typecheck check \
        dev-db local-test install-frontend

help: ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

env: ## Create local .env files from the shipped examples
	@test -f .env || (cp .env.example .env && echo "created .env")
	@test -f backend/.env || (cp backend/.env.example backend/.env && echo "created backend/.env")

up: env ## Build and start postgres, redis, backend, celery and frontend
	$(COMPOSE) up -d --build
	@echo "API:      http://localhost:$${BACKEND_PORT:-8000}/api/v1/health"
	@echo "API docs: http://localhost:$${BACKEND_PORT:-8000}/api/docs"
	@echo "Frontend: http://localhost:$${FRONTEND_PORT:-5173}"

down: ## Stop all services (keeps volumes)
	$(COMPOSE) down

logs: ## Tail logs for every service
	$(COMPOSE) logs -f

logs-api: ## Tail backend logs
	$(COMPOSE) logs -f backend

logs-worker: ## Tail celery worker logs
	$(COMPOSE) logs -f celery-worker

psql: ## Open a psql shell on the application database
	$(COMPOSE) exec postgres psql -U $${POSTGRES_USER:-xgeo} -d $${POSTGRES_DB:-xgeo_db}

shell: ## Open a bash shell inside the backend container
	$(BACKEND) bash

migrate: ## Apply all Alembic migrations
	$(BACKEND) alembic upgrade head

migration: ## Autogenerate a migration: make migration msg="add x"
	@test -n "$(msg)" || (echo "usage: make migration msg=\"description\"" && exit 1)
	$(BACKEND) alembic revision --autogenerate -m "$(msg)"

migrate-down: ## Roll back one migration
	$(BACKEND) alembic downgrade -1

seed: ## Populate the database with demo data
	$(BACKEND) python scripts/seed_db.py

test: ## Run the full backend test suite with coverage
	$(BACKEND) env XGEO_REQUIRE_DB=1 pytest -v --cov=app --cov-report=term-missing

test-unit: ## Run unit tests only (no database required)
	$(BACKEND) pytest tests/unit -v

test-integration: ## Run integration tests only (database required)
	$(BACKEND) env XGEO_REQUIRE_DB=1 pytest tests/integration -v

test-e2e: ## Run end-to-end tests only (database + local HTTP fixture server)
	$(BACKEND) env XGEO_REQUIRE_DB=1 pytest tests/e2e -v

coverage: ## Generate an HTML coverage report into backend/htmlcov
	$(BACKEND) pytest --cov=app --cov-report=html

format: ## Format the backend with black + isort
	$(BACKEND) black app tests scripts
	$(BACKEND) isort app tests scripts

lint: ## Lint the backend with ruff
	$(BACKEND) ruff check app tests scripts

typecheck: ## Type-check the frontend (tsc --noEmit) and backend (mypy)
	cd frontend && npm run typecheck
	$(BACKEND) mypy app || true

check: lint test ## Lint + full test suite

install-frontend: ## Install frontend dependencies
	cd frontend && npm install

# --- Docker-free local development ------------------------------------------
dev-db: ## Start a bundled PostgreSQL 16 + pgvector without Docker (pgserver)
	cd backend && $(PYTHON) scripts/dev_db.py start

local-test: ## Run the backend suite against the bundled PostgreSQL (no Docker)
	cd backend && XGEO_REQUIRE_DB=1 $(PYTHON) -m pytest tests -v
