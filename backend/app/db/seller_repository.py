from __future__ import annotations

from datetime import date
from typing import Iterable, List, Optional

from ..schemas.seller import (
    CompetitorRecord,
    InventoryRecord,
    Product,
    ReviewRecord,
    SalesRecord,
)
from .init_seller_warehouse import (
    COMPETITORS_TABLE,
    INVENTORY_TABLE,
    PRODUCTS_TABLE,
    REVIEWS_TABLE,
    SALES_HISTORY_TABLE,
)
from .session import get_warehouse_connection


def _rows_to_models(rows: Iterable[dict], model_cls):
    """
    Helper to convert DuckDB result rows into Pydantic models.
    """
    return [model_cls.model_validate(row) for row in rows]


def list_products(limit: int = 100, offset: int = 0) -> List[Product]:
    """
    Return a page of products from the warehouse.
    """
    with get_warehouse_connection() as conn:
        df = conn.execute(
            f"""
            SELECT *
            FROM {PRODUCTS_TABLE}
            LIMIT ?
            OFFSET ?
            """,
            [limit, offset],
        ).df()

    return _rows_to_models(df.to_dict(orient="records"), Product)


def get_product(product_id: str) -> Optional[Product]:
    """
    Fetch a single product by product_id.
    """
    with get_warehouse_connection() as conn:
        df = conn.execute(
            f"""
            SELECT *
            FROM {PRODUCTS_TABLE}
            WHERE product_id = ?
            """,
            [product_id],
        ).df()

    if df.empty:
        return None

    row = df.to_dict(orient="records")[0]
    return Product.model_validate(row)


def list_competitors(product_id: str) -> List[CompetitorRecord]:
    """
    Return competitor records for a given product_id.
    """
    with get_warehouse_connection() as conn:
        df = conn.execute(
            f"""
            SELECT *
            FROM {COMPETITORS_TABLE}
            WHERE product_id = ?
            """,
            [product_id],
        ).df()

    return _rows_to_models(df.to_dict(orient="records"), CompetitorRecord)


def get_inventory(product_id: str) -> Optional[InventoryRecord]:
    """
    Return inventory position for a given product_id, if any.
    """
    with get_warehouse_connection() as conn:
        df = conn.execute(
            f"""
            SELECT *
            FROM {INVENTORY_TABLE}
            WHERE product_id = ?
            """,
            [product_id],
        ).df()

    if df.empty:
        return None

    row = df.to_dict(orient="records")[0]
    return InventoryRecord.model_validate(row)


def list_reviews(product_id: str, limit: int = 100) -> List[ReviewRecord]:
    """
    Return recent reviews for a given product.
    """
    with get_warehouse_connection() as conn:
        df = conn.execute(
            f"""
            SELECT *
            FROM {REVIEWS_TABLE}
            WHERE product_id = ?
            ORDER BY date DESC
            LIMIT ?
            """,
            [product_id, limit],
        ).df()

    return _rows_to_models(df.to_dict(orient="records"), ReviewRecord)


def list_sales_history(
    product_id: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> List[SalesRecord]:
    """
    Return sales history for a given product, optionally filtered by date range.
    """
    conditions = ["product_id = ?"]
    params: List[object] = [product_id]

    if start_date is not None:
        conditions.append("date >= ?")
        params.append(start_date)

    if end_date is not None:
        conditions.append("date <= ?")
        params.append(end_date)

    where_clause = " AND ".join(conditions)

    with get_warehouse_connection() as conn:
        df = conn.execute(
            f"""
            SELECT *
            FROM {SALES_HISTORY_TABLE}
            WHERE {where_clause}
            ORDER BY date
            """,
            params,
        ).df()

    return _rows_to_models(df.to_dict(orient="records"), SalesRecord)


def list_top_products_by_revenue(limit: int = 50) -> List[Product]:
    """
    Return the top-N products ordered by total gross revenue.

    This is used by the Product Selector Agent to choose a subset of SKUs
    to focus on for deeper analysis.
    """
    with get_warehouse_connection() as conn:
        df = conn.execute(
            f"""
            SELECT
                p.*,
                COALESCE(SUM(s.gross_revenue), 0.0) AS total_revenue
            FROM {PRODUCTS_TABLE} p
            LEFT JOIN {SALES_HISTORY_TABLE} s
              ON p.product_id = s.product_id
            GROUP BY ALL
            ORDER BY total_revenue DESC
            LIMIT ?
            """,
            [limit],
        ).df()

    # We ignore total_revenue when constructing Product models.
    return _rows_to_models(df.to_dict(orient="records"), Product)
