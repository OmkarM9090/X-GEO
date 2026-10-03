"""FastAPI application factory.

Layering: ``main.py`` wires middleware, exception handlers and routers — nothing
else. All behaviour lives in services, all SQL in repositories.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.v1.router import api_v1_router
from app.config import Settings, get_settings
from app.core.database import dispose_engine, init_models
from app.core.exceptions import AppError
from app.core.logging_config import configure_logging, get_logger
from app.core.middleware import RequestLoggingMiddleware, TenantContextMiddleware
from app.schemas.common import ErrorResponse

logger = get_logger(__name__)

DESCRIPTION = """
**X-GEO** powers Generative Engine Optimization for B2B teams: it crawls a page,
scores its technical readiness, semantic alignment, evidentiary density and
machine readability (the **PCS** index), and prepares the retrieval corpus used
by the citation simulator.

* Architecture: Repository → Service → Controller (routes never touch the DB)
* Storage: PostgreSQL + pgvector + full-text search
* Async work: Celery + Redis (crawl pipeline)
* Auth: Supabase JWT (HS256 or JWKS-verified asymmetric keys)
""".strip()


def _request_id(request: Request) -> str | None:
    return request.headers.get(get_settings().REQUEST_ID_HEADER)


def _error_response(
    *,
    status_code: int,
    message: str,
    code: str,
    detail: Any = None,
    details: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    request_id: str | None = None,
) -> JSONResponse:
    payload = ErrorResponse(
        message=message,
        code=code,
        detail=detail if detail is not None else message,
        request_id=request_id,
        details=details or {},
    )
    return JSONResponse(status_code=status_code, content=payload.model_dump(), headers=headers)


def register_exception_handlers(app: FastAPI) -> None:
    """Uniform, logged error responses for every failure mode."""

    @app.exception_handler(AppError)
    async def _app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        if exc.status_code >= 500:
            logger.error(
                "request.app_error", code=exc.code, detail=exc.detail, status=exc.status_code
            )
        return _error_response(
            status_code=exc.status_code,
            message=exc.message,
            code=exc.code,
            details=exc.details,
            headers=exc.headers,
            request_id=_request_id(request),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        return _error_response(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message="Request validation failed",
            code="validation_error",
            detail=exc.errors(),
            details={"errors": exc.errors()},
            request_id=_request_id(request),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        return _error_response(
            status_code=exc.status_code,
            message=str(exc.detail),
            code="http_error",
            headers=getattr(exc, "headers", None),
            request_id=_request_id(request),
        )

    @app.exception_handler(Exception)
    async def _unhandled_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:  # pragma: no cover
        logger.exception("request.unhandled_error", error=str(exc), path=str(request.url.path))
        return _error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Internal server error",
            code="internal_error",
            request_id=_request_id(request),
        )


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Startup/shutdown hook: logging, optional table creation, clean shutdown."""
    settings = get_settings()
    configure_logging(settings, force=True)
    logger.info(
        "app.starting",
        app=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        database_host=settings.database_host,
        auth_configured=settings.supabase_auth_configured,
    )

    if settings.AUTO_CREATE_TABLES:
        if settings.ENVIRONMENT == "production":
            logger.warning("app.auto_create_tables_enabled_in_production")
        try:
            await init_models()
        except Exception as exc:
            logger.error("app.init_models_failed", error=str(exc))

    try:
        yield
    finally:
        # Shut down the headless browser if it was ever started.
        try:
            from app.crawler.playwright_fallback import shutdown_renderer

            await shutdown_renderer()
        except Exception as exc:
            logger.warning("app.playwright_shutdown_failed", error=str(exc))
        await dispose_engine()
        logger.info("app.stopped")


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the FastAPI application (import-safe, used by tests too)."""
    settings = settings or get_settings()
    docs_enabled = settings.DEBUG or settings.ENVIRONMENT != "production"

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=DESCRIPTION,
        lifespan=lifespan,
        docs_url="/api/docs" if docs_enabled else None,
        redoc_url="/api/redoc" if docs_enabled else None,
        openapi_url="/api/openapi.json" if docs_enabled else None,
        contact={"name": "X-GEO", "url": "https://x-geo.dev"},
        license_info={"name": "Proprietary"},
        openapi_tags=[
            {"name": "Health", "description": "Liveness, readiness and dependency probes."},
            {"name": "Auth", "description": "Supabase-backed signup, signin and refresh."},
            {"name": "Projects", "description": "Domains the account is optimising."},
            {"name": "Audits", "description": "Scored analyses of individual pages."},
            {"name": "Crawls", "description": "Crawl jobs and their progress."},
        ],
    )

    # --- Middleware (added innermost first) ---------------------------------
    app.add_middleware(TenantContextMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(GZipMiddleware, minimum_size=1024)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_origin_regex=settings.cors_origin_regex,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=[
            settings.REQUEST_ID_HEADER,
            "X-Process-Time-Ms",
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
        ],
        max_age=600,
    )
    if settings.ALLOWED_HOSTS and "*" not in settings.ALLOWED_HOSTS:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS)

    register_exception_handlers(app)
    app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)

    @app.get("/", include_in_schema=False)
    async def root() -> dict[str, Any]:
        """Service banner with pointers to the docs and probes."""
        return {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "docs": "/api/docs" if docs_enabled else None,
            "health": f"{settings.API_V1_PREFIX}/health",
            "openapi": "/api/openapi.json" if docs_enabled else None,
        }

    return app


app = create_app()


__all__ = ["app", "create_app", "lifespan", "register_exception_handlers"]
