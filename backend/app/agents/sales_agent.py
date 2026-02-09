from __future__ import annotations

from typing import Dict, List

from ..db import seller_repository
from ..observability.logging import get_logger
from ..tools.sales_tool import (
    ProductSalesOverviewInput,
    ProductSalesOverviewOutput,
    get_product_sales_overview,
)
from .state import SalesAnalysis, SellerState

logger = get_logger("agents.sales")


def _choose_product_ids_for_sales(
    state: SellerState,
    max_products: int = 10,
) -> List[str]:
    """
    Decide which products should be analyzed by the Sales Agent.

    Priority:
      1) If product_selection.selected_product_ids is non-empty, use those.
      2) Otherwise, fall back to the first `max_products` from the warehouse.
    """
    if (
        state.product_selection is not None
        and state.product_selection.selected_product_ids
    ):
        return state.product_selection.selected_product_ids

    # Fallback: basic catalog slice
    products = seller_repository.list_products(limit=max_products, offset=0)
    return [p.product_id for p in products]


def _build_narrative(overview: ProductSalesOverviewOutput) -> str:
    """
    Build a simple, deterministic narrative for sales performance.

    Later, this can be replaced or enriched by an LLM call, but the structure
    stays the same so downstream agents don't break.
    """
    s = overview.summary

    bits: List[str] = []

    bits.append(
        f"Total units sold: {s.total_units_sold}, "
        f"gross revenue: {s.total_gross_revenue:.2f}, "
        f"returns: {s.total_returns}."
    )

    if s.total_page_views > 0:
        bits.append(f"Page views: {s.total_page_views}.")
    if s.avg_selling_price is not None:
        bits.append(f"Average selling price: {s.avg_selling_price:.2f}.")
    if s.conversion_rate is not None:
        bits.append(f"Conversion rate (approx): {s.conversion_rate:.4f}.")

    if s.total_units_sold == 0:
        bits.append("The product has no recorded sales in the selected period.")
    elif s.conversion_rate is not None and s.conversion_rate < 0.01:
        bits.append(
            "Conversion rate is quite low; consider improving listing quality or pricing."
        )
    else:
        bits.append("Sales performance is non-zero; further analysis can refine this.")

    return " ".join(bits)


def update_sales_analyses(
    state: SellerState,
    max_products: int = 10,
) -> SellerState:
    """
    Sales Agent.

    Responsibilities:
      - Decide which products to analyze.
      - For each product, use the sales_tool to fetch:
          * summary metrics
          * time series
      - Convert these into SalesAnalysis entries in SellerState.

    This agent:
      - does NOT read CSVs directly
      - does NOT query DuckDB directly (except for choosing fallback products),
        actual metrics come from the tools layer.
    """
    product_ids = _choose_product_ids_for_sales(state, max_products=max_products)

    if not product_ids:
        logger.info("Sales agent: no products to analyze")
        return state

    logger.info(
        "Sales agent analyzing products",
        extra={"num_products": len(product_ids)},
    )

    # Index existing analyses by product_id so we can overwrite/update cleanly
    existing_by_product: Dict[str, SalesAnalysis] = {
        a.product_id: a for a in state.sales_analyses
    }

    updated_by_product: Dict[str, SalesAnalysis] = {}

    for product_id in product_ids:
        try:
            overview = get_product_sales_overview(
                ProductSalesOverviewInput(product_id=product_id)
            )
        except ValueError as exc:
            # e.g., product not found → log and skip
            logger.warning(
                "Sales agent: could not get overview for product",
                extra={"product_id": product_id, "error": str(exc)},
            )
            continue

        s = overview.summary

        analysis = SalesAnalysis(
            product_id=product_id,
            total_units_sold=s.total_units_sold,
            total_gross_revenue=s.total_gross_revenue,
            total_returns=s.total_returns,
            total_page_views=s.total_page_views,
            avg_selling_price=s.avg_selling_price,
            conversion_rate=s.conversion_rate,
            narrative=_build_narrative(overview),
        )

        updated_by_product[product_id] = analysis

    merged: Dict[str, SalesAnalysis] = {**existing_by_product, **updated_by_product}
    state.sales_analyses = list(merged.values())

    logger.info(
        "Sales agent updated sales analyses",
        extra={"num_analyses": len(state.sales_analyses)},
    )

    return state
