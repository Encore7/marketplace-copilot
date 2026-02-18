from __future__ import annotations

from typing import List

from ..db import seller_repository
from ..observability.logging import get_logger
from .state import ProductFilter, ProductSelection, SellerState

logger = get_logger("agents.product_selector")


def update_product_selection(
    state: SellerState,
    max_products: int = 20,
) -> SellerState:
    """
    Product Selector Agent.

    Responsibilities:
      - Choose a subset of SKUs to focus on for deeper analysis.
      - For now, we pick top-N products by gross revenue.
      - In future, we can incorporate:
          * explicit product filters from the user
          * marketplaces
          * risk-based selection (e.g. high returns, low conversion)

    This agent writes into `state.product_selection`.
    """
    if (
        state.product_selection is not None
        and state.product_selection.selected_product_ids
    ):
        logger.info(
            "Product selector: existing selection present; leaving as-is",
            extra={
                "num_selected": len(state.product_selection.selected_product_ids),
            },
        )
        return state

    # Pull top products by revenue from the warehouse.
    top_products = seller_repository.list_top_products_by_revenue(limit=max_products)
    product_ids: List[str] = [p.product_id for p in top_products]

    if not product_ids:
        logger.info("Product selector: no products found in warehouse")
        # Still ensure structure exists, with empty selection.
        state.product_selection = ProductSelection(
            filter=ProductFilter(),
            selected_product_ids=[],
            notes="No products found in warehouse.",
        )
        return state

    state.product_selection = ProductSelection(
        filter=ProductFilter(),
        selected_product_ids=product_ids,
        notes=(
            "Selected top products by gross revenue from the warehouse. "
            "This is a heuristic and can be refined with explicit filters."
        ),
    )

    logger.info(
        "Product selector chose products",
        extra={"num_selected": len(product_ids)},
    )

    return state
