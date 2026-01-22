from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

import duckdb

from ..core.config import settings


@contextmanager
def get_warehouse_connection() -> Iterator[duckdb.DuckDBPyConnection]:
    """
    Context manager for the seller warehouse connection.

    The DSN comes from settings.warehouse.seller_warehouse_dsn and can be
    switched to Postgres/Snowflake/etc. later without changing call sites.
    """
    conn = duckdb.connect(settings.warehouse.seller_warehouse_dsn)
    try:
        yield conn
    finally:
        conn.close()
