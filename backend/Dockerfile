# =============================================================================
# X-GEO backend image — FastAPI + Scrapy + Playwright + Celery
# =============================================================================
# Build:  docker build -t x-geo-backend ./backend
# Dev:    INSTALL_DEV=true (default) also installs ruff/black/mypy/pytest
# =============================================================================
FROM python:3.11-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    TZ=UTC

# System deps: libpq for asyncpg/alembic, lxml headers + toolchain as a
# fallback when a wheel is unavailable for the target architecture.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        libxml2-dev \
        libxslt1-dev \
        curl \
        git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# --- Python dependencies (cached layer) -------------------------------------
COPY requirements.txt requirements-dev.txt ./
ARG INSTALL_DEV=true
RUN if [ "$INSTALL_DEV" = "true" ]; then \
        pip install --no-cache-dir -r requirements-dev.txt; \
    else \
        pip install --no-cache-dir -r requirements.txt; \
    fi

# --- Playwright browsers (Chromium only) ------------------------------------
RUN playwright install --with-deps chromium

# --- Application code -------------------------------------------------------
COPY . .

# --- Unprivileged runtime user ---------------------------------------------
RUN groupadd --system --gid 1001 xgeo \
    && useradd --system --uid 1001 --gid xgeo --create-home xgeo \
    && chown -R xgeo:xgeo /app /ms-playwright
USER xgeo

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -fsS http://localhost:8000/api/v1/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
