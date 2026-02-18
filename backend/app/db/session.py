from __future__ import annotations

import errno
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import duckdb

from ..core.config import settings


def _resolve_duckdb_path(raw_dsn: str) -> str:
    """
    Resolve DuckDB DSN/path into a concrete filesystem path understood by duckdb.connect.

    Supported inputs:
      - "duckdb:///absolute/or/relative/path.duckdb"
      - "/absolute/path.duckdb"
      - "relative/path.duckdb"
      - ":memory:"
    """
    if raw_dsn == ":memory:":
        return raw_dsn

    dsn = raw_dsn.strip()
    if dsn.startswith("duckdb:///"):
        dsn = dsn[len("duckdb:///") :]
        if not dsn.startswith("/"):
            dsn = "/" + dsn

    path = Path(dsn)
    if not path.is_absolute():
        path = Path.cwd() / path

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        if path.as_posix().startswith("/app_storage/") and exc.errno in (
            errno.EPERM,
            errno.EACCES,
            errno.EROFS,
        ):
            path = Path.cwd() / path.as_posix().lstrip("/")
            path.parent.mkdir(parents=True, exist_ok=True)
        else:
            raise
    return path.as_posix()


@contextmanager
def get_warehouse_connection() -> Iterator[duckdb.DuckDBPyConnection]:
    """
    Context manager for the seller warehouse connection.

    The DSN comes from settings.warehouse.seller_warehouse_dsn and can be
    switched to Postgres/Snowflake/etc. later without changing call sites.
    """
    db_path = _resolve_duckdb_path(settings.warehouse.seller_warehouse_dsn)
    conn = duckdb.connect(db_path)
    try:
        yield conn
    finally:
        conn.close()
