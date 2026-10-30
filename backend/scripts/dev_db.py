#!/usr/bin/env python3
"""Start a local PostgreSQL 16 + pgvector server **without Docker**.

Uses the ``pgserver`` package (a pip-installable PostgreSQL build that bundles
the `vector` extension) so contributors and CI sandboxes can run the full stack
— migrations, tests, seeding — with a single command::

    python scripts/dev_db.py start      # start + create databases
    python scripts/dev_db.py status     # show the connection URL
    python scripts/dev_db.py stop       # stop the server
    python scripts/dev_db.py url        # print DATABASE_URL for .env

The data directory defaults to ``backend/.pgdata`` (git-ignored). Set
``XGEO_PGDATA`` to relocate it, or ``XGEO_PG_PORT``/``XGEO_PG_HOST`` to expose a
TCP port instead of the unix socket.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PGDATA = BACKEND_ROOT / ".pgdata"
APP_DB = "xgeo_db"
TEST_DB = "xgeo_test_db"
EXTENSIONS = ("vector", "pg_trgm")


def _require_pgserver():
    try:
        import pgserver  # type: ignore[import-not-found]
    except ImportError:
        print(
            "pgserver is not installed.\n"
            "Install the local-db extra:  pip install -e '.[local-db]'\n"
            "or use Docker:               make up",
            file=sys.stderr,
        )
        raise SystemExit(2) from None
    return pgserver


def _pgdata() -> Path:
    return Path(os.environ.get("XGEO_PGDATA", DEFAULT_PGDATA)).expanduser().resolve()


def _to_async_url(uri: str, database: str | None = None) -> str:
    url = uri.replace("postgresql://", "postgresql+asyncpg://", 1)
    if database:
        head, _, query = url.partition("?")
        base, _, _old_db = head.rpartition("/")
        url = f"{base}/{database}"
        if query:
            url = f"{url}?{query}"
    return url


def start(*, expose_tcp: bool = False, quiet: bool = False) -> str:
    """Start the bundled server and ensure the app/test databases exist."""
    pgserver = _require_pgserver()
    pgdata = _pgdata()
    pgdata.mkdir(parents=True, exist_ok=True)

    try:
        server = pgserver.get_server(pgdata, cleanup_mode=None)
    except TypeError:  # pragma: no cover - older pgserver signatures
        server = pgserver.get_server(pgdata)

    uri = server.get_uri()  # postgres://postgres@/postgres?host=/tmp/...
    existing = server.psql("SELECT datname FROM pg_database;")
    for database in (APP_DB, TEST_DB):
        if database not in existing:
            server.psql(f'CREATE DATABASE "{database}";')
        for extension in EXTENSIONS:
            try:
                server.psql(f"\\connect {database}\nCREATE EXTENSION IF NOT EXISTS {extension};")
            except subprocess.CalledProcessError as exc:  # pragma: no cover - optional extension
                print(
                    f"warning: could not enable {extension} in {database}: {exc}", file=sys.stderr
                )

    if expose_tcp:
        print(
            "note: pgserver listens on a unix socket only; point DATABASE_URL at "
            "the socket URL printed below.",
            file=sys.stderr,
        )

    app_url = _to_async_url(uri, APP_DB)
    test_url = _to_async_url(uri, TEST_DB)
    if not quiet:
        print(f"PostgreSQL data directory : {pgdata}")
        print(f"DATABASE_URL              : {app_url}")
        print(f"TEST_DATABASE_URL         : {test_url}")
        print("\nAdd to backend/.env:")
        print(f"DATABASE_URL={app_url}")
    return app_url


def stop() -> None:
    """Stop the server (data directory is preserved)."""
    pgserver = _require_pgserver()
    pgdata = _pgdata()
    if not (pgdata / "postmaster.pid").exists():
        print("no running server found")
        return
    bin_dir = Path(pgserver.__file__).parent / "pginstall" / "bin"
    subprocess.run(
        [str(bin_dir / "pg_ctl"), "-D", str(pgdata), "-w", "stop"],
        check=False,
    )
    print("stopped")


def status() -> None:
    """Print the connection URLs of the running server."""
    pgserver = _require_pgserver()
    pgdata = _pgdata()
    if not (pgdata / "PG_VERSION").exists():
        print("not initialised - run 'python scripts/dev_db.py start'")
        return
    server = pgserver.get_server(pgdata, cleanup_mode=None)
    uri = server.get_uri()
    print(f"DATABASE_URL              : {_to_async_url(uri, APP_DB)}")
    print(f"TEST_DATABASE_URL         : {_to_async_url(uri, TEST_DB)}")
    print(server.psql("SELECT version();").strip())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "command", choices=["start", "stop", "status", "url"], nargs="?", default="start"
    )
    parser.add_argument(
        "--tcp", action="store_true", help="inform about TCP exposure (sockets are used by default)"
    )
    args = parser.parse_args(argv)

    if args.command == "start":
        start(expose_tcp=args.tcp)
    elif args.command == "stop":
        stop()
    elif args.command == "status":
        status()
    else:
        print(
            _to_async_url(
                _require_pgserver().get_server(_pgdata(), cleanup_mode=None).get_uri(), APP_DB
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
