"""Alembic environment (async engine, settings-driven URL).

The database URL comes from :class:`app.config.Settings` (``DATABASE_URL``), so
migrations always target the same database as the application. Override it for
one-off runs with ``alembic -x db_url=postgresql+asyncpg://... upgrade head``.
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.config import get_settings
from app.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

settings = get_settings()

# `-x db_url=...` wins, then the application settings.
x_arguments = context.get_x_argument(as_dictionary=True)
database_url = x_arguments.get("db_url") or settings.DATABASE_URL
config.set_main_option("sqlalchemy.url", database_url)

target_metadata = Base.metadata

#: Objects Alembic should never try to manage.
EXCLUDED_TABLES = {"spatial_ref_sys"}


def include_object(
    object_: object, name: str | None, type_: str, reflected: bool, compare_to: object
) -> bool:
    return not (type_ == "table" and name in EXCLUDED_TABLES)


def _configure(*, connection: Connection | None = None, **kwargs: object) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=False,
        include_object=include_object,
        include_schemas=False,
        render_as_batch=False,
        **kwargs,
    )


def run_migrations_offline() -> None:
    """Emit SQL to stdout without connecting (``alembic upgrade head --sql``)."""
    _configure(
        url=database_url,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    _configure(connection=connection)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
