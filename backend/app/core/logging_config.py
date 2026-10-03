"""Structured logging configuration (structlog + stdlib bridge).

Usage::

    from app.core.logging_config import configure_logging, get_logger

    configure_logging()                 # once, at application startup
    log = get_logger(__name__)
    log.info("audit.created", audit_id=str(audit.id), project_id=str(project.id))

Request-scoped values (request id, tenant, user) are bound through
``structlog.contextvars`` by the middleware, so they appear on every log line
emitted while handling a request.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog
from structlog.contextvars import bind_contextvars, clear_contextvars

from app.config import Settings, get_settings

_configured = False

#: Third-party loggers that are far too chatty at INFO level.
_NOISY_LOGGERS = {
    "scrapy": logging.WARNING,
    "scrapy.core.engine": logging.WARNING,
    "scrapy.utils.log": logging.WARNING,
    "twisted": logging.WARNING,
    "asyncio": logging.WARNING,
    "urllib3": logging.WARNING,
    "httpx": logging.WARNING,
    "httpcore": logging.WARNING,
    "python_multipart": logging.WARNING,
    "playwright": logging.WARNING,
}


def configure_logging(
    settings: Settings | None = None,
    *,
    level: str | None = None,
    json_logs: bool | None = None,
    force: bool = False,
) -> None:
    """Configure structlog + the stdlib root logger.

    Idempotent: repeated calls are ignored unless ``force=True``.
    """
    global _configured
    if _configured and not force:
        return

    settings = settings or get_settings()
    log_level = (level or settings.LOG_LEVEL).upper()
    use_json = settings.LOG_JSON if json_logs is None else json_logs

    numeric_level = getattr(logging, log_level, logging.INFO)

    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    renderer: Any = (
        structlog.processors.JSONRenderer()
        if use_json
        else structlog.dev.ConsoleRenderer(colors=sys.stderr.isatty())
    )

    # stdlib-backed factory: the renderer emits the complete line (timestamp,
    # level, logger name) and the stdlib handler only writes the message. Using
    # ``PrintLoggerFactory`` here would break ``add_logger_name`` and hide
    # third-party (Scrapy/Twisted) loggers from the root handler.
    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(
        format="%(message)s",
        level=numeric_level,
        stream=sys.stderr,
        force=True,
    )
    for name, logger_level in _NOISY_LOGGERS.items():
        logging.getLogger(name).setLevel(logger_level)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.DATABASE_ECHO else logging.WARNING
    )

    _configured = True


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a bound structlog logger."""
    return structlog.get_logger(name)  # type: ignore[return-value]


def bind_request_context(**values: Any) -> None:
    """Bind request-scoped values for every subsequent log line."""
    bind_contextvars(**{key: value for key, value in values.items() if value is not None})


def clear_request_context() -> None:
    """Clear request-scoped context (always call at the end of a request)."""
    clear_contextvars()
