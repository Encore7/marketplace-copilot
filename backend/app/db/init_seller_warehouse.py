from __future__ import annotations

from pathlib import Path
from typing import Final

import pandas as pd

from ..core.config import settings
from ..db.session import get_warehouse_connection

# Table names we expect in the warehouse.
PRODUCTS_TABLE: Final[str] = "products"
COMPETITORS_TABLE: Final[str] = "competitors"
INVENTORY_TABLE: Final[str] = "inventory"
REVIEWS_TABLE: Final[str] = "reviews"
SALES_HISTORY_TABLE: Final[str] = "sales_history"


def _load_csv(path: Path) -> pd.DataFrame:
    """
    Read CSV resiliently for messy real-world seller exports.
    """
    return pd.read_csv(
        path,
        engine="python",
        on_bad_lines="skip",
    )


def _write_table(conn, table_name: str, df: pd.DataFrame) -> None:
    temp_name = f"_{table_name}_df"
    conn.register(temp_name, df)
    conn.execute(f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM {temp_name}")
    conn.unregister(temp_name)


def init_seller_warehouse() -> None:
    """
    Initialize and (re)load the seller warehouse from CSV files.

    This function is intended to be run as an offline ETL step (CLI, job, etc.),
    NOT on every API startup and definitely not per request.
    """
    data_root = Path(settings.warehouse.seller_data_root)

    products_csv = data_root / "products.csv"
    competitors_csv = data_root / "competitors.csv"
    inventory_csv = data_root / "inventory.csv"
    reviews_csv = data_root / "reviews.csv"
    sales_history_csv = data_root / "sales_history.csv"

    with get_warehouse_connection() as conn:
        _write_table(conn, PRODUCTS_TABLE, _load_csv(products_csv))
        _write_table(conn, COMPETITORS_TABLE, _load_csv(competitors_csv))
        _write_table(conn, INVENTORY_TABLE, _load_csv(inventory_csv))
        _write_table(conn, REVIEWS_TABLE, _load_csv(reviews_csv))
        _write_table(conn, SALES_HISTORY_TABLE, _load_csv(sales_history_csv))


if __name__ == "__main__":
    init_seller_warehouse()
