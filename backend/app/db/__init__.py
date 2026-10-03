"""Database session helpers.

:mod:`app.core.database` owns engine/session construction. This package is the
*stable import surface* for infrastructure callers — Celery tasks, scripts and
worker entrypoints — so that internals can move without touching call sites::

    from app.db import session_scope, task_session

It deliberately contains no logic of its own.
"""

from __future__ import annotations

from app.core.database import (
    DatabaseHealth,
    async_session_factory,
    check_database_health,
    create_task_engine,
    dispose_engine,
    drop_models,
    engine,
    get_db,
    init_models,
    session_scope,
    task_session,
)
from app.models.base import Base

__all__ = [
    "Base",
    "DatabaseHealth",
    "async_session_factory",
    "check_database_health",
    "create_task_engine",
    "dispose_engine",
    "drop_models",
    "engine",
    "get_db",
    "init_models",
    "session_scope",
    "task_session",
]
