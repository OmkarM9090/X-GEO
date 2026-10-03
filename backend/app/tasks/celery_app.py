"""Celery application (Redis broker + result backend).

Run the worker with::

    celery -A app.tasks.celery_app:celery_app worker --loglevel=info --concurrency=4

Tasks are *thin*: they open their own database session
(:func:`app.core.database.task_session`), delegate to the service layer and
return JSON-serialisable summaries.
"""

from __future__ import annotations

from typing import Any

from celery import Celery
from celery.signals import setup_logging, worker_ready

from app.config import get_settings
from app.core.logging_config import configure_logging, get_logger

settings = get_settings()

celery_app = Celery(
    "x-geo",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.crawl_tasks",
        "app.tasks.simulation_tasks",
    ],
)

celery_app.conf.update(
    # Serialisation
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    # Time
    timezone="UTC",
    enable_utc=True,
    # Reliability
    task_track_started=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    # Limits
    task_time_limit=settings.TASK_TIME_LIMIT_SECONDS,
    task_soft_time_limit=settings.TASK_SOFT_TIME_LIMIT_SECONDS,
    task_default_retry_delay=2,
    task_max_retries=settings.TASK_MAX_RETRIES,
    result_expires=settings.TASK_RESULT_EXPIRES_SECONDS,
    # Routing
    task_default_queue="xgeo",
    task_routes={
        "app.tasks.crawl_tasks.*": {"queue": "xgeo.crawl"},
        "app.tasks.simulation_tasks.*": {"queue": "xgeo.simulation"},
    },
    # Tests / local development without a worker
    task_always_eager=settings.TASK_ALWAYS_EAGER,
    task_eager_propagates=True,
    # Housekeeping: recover jobs orphaned by a crashed worker.
    beat_schedule={
        "recover-stale-crawl-jobs": {
            "task": "app.tasks.crawl_tasks.recover_stale_jobs",
            "schedule": 300.0,
        },
        "cleanup-orphan-chunks": {
            "task": "app.tasks.crawl_tasks.cleanup_orphan_chunks",
            "schedule": 3600.0,
        },
    },
)


@setup_logging.connect
def _configure_celery_logging(**kwargs: Any) -> None:  # noqa: ARG001
    """Use the application's structured logging inside workers."""
    configure_logging(settings, json_logs=settings.LOG_JSON, force=True)


@worker_ready.connect
def _log_worker_ready(**kwargs: Any) -> None:  # noqa: ARG001
    get_logger(__name__).info(
        "celery.worker_ready",
        broker=settings.REDIS_URL.split("@")[-1],
        queues=["xgeo.crawl", "xgeo.simulation"],
    )


__all__ = ["celery_app"]
