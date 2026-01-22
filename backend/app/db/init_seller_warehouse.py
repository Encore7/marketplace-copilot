from __future__ import annotations

from pathlib import Path
from typing import Final

from ..core.config import settings
from ..db.session import get_warehouse_connection

# Table names we expect in the warehouse.
PRODUCTS_TABLE: Final[str] = "products"
COMPETITORS_TABLE: Final[str] = "competitors"
INVENTORY_TABLE: Final[str] = "inventory"
REVIEWS_TABLE: Final[str] = "reviews"
SALES_HISTORY_TABLE: Final[str] = "sales_history"


def init_seller_warehouse() -> None:
    """
    Initialize and (re)load the seller warehouse from CSV files.

    This function is intended to be run as an offline ETL step (CLI, job, etc.),
    NOT on every API startup and definitely not per request.

    It:
    - Reads CSVs under settings.warehouse.seller_data_root
    - Creates/replaces DuckDB tables
    """
    data_root = Path(settings.warehouse.seller_data_root)

    products_csv = data_root / "products.csv"
    competitors_csv = data_root / "competitors.csv"
    inventory_csv = data_root / "inventory.csv"
    reviews_csv = data_root / "reviews.csv"
    sales_history_csv = data_root / "sales_history.csv"

    with get_warehouse_connection() as conn:
        # We use CREATE OR REPLACE to keep this idempotent
        conn.execute(
            f"""
            CREATE OR REPLACE TABLE {PRODUCTS_TABLE} AS
            SELECT * FROM read_csv_auto('{products_csv.as_posix()}', header=True);
            """
        )

        conn.execute(
            f"""
            CREATE OR REPLACE TABLE {COMPETITORS_TABLE} AS
            SELECT * FROM read_csv_auto('{competitors_csv.as_posix()}', header=True);
            """
        )

        conn.execute(
            f"""
            CREATE OR REPLACE TABLE {INVENTORY_TABLE} AS
            SELECT * FROM read_csv_auto('{inventory_csv.as_posix()}', header=True);
            """
        )

        conn.execute(
            f"""
            CREATE OR REPLACE TABLE {REVIEWS_TABLE} AS
            SELECT * FROM read_csv_auto('{reviews_csv.as_posix()}', header=True);
            """
        )

        conn.execute(
            f"""
            CREATE OR REPLACE TABLE {SALES_HISTORY_TABLE} AS
            SELECT * FROM read_csv_auto('{sales_history_csv.as_posix()}', header=True);
            """
        )


if __name__ == "__main__":
    init_seller_warehouse()
