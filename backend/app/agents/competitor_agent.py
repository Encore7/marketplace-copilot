from __future__ import annotations

from typing import Dict, List

from ..db import seller_repository
from ..observability.logging import get_logger
from ..tools.competitor_tool import (
    CompetitorOverviewInput,
    CompetitorOverviewOutput,
    get_competitor_overview,
)
from .state import CompetitorAnalysis, SellerState

logger = get_logger("agents.competitor")


def _choose_product_ids_for_competitors(
    state: SellerState,
    max_products: int = 10,
) -> List[str]:
    """
    Decide which products should be analyzed by the Competitor Agent.

    Priority:
      1) ProductSelection.selected_product_ids, if present
      2) Fallback: first N products from the catalog
    """
    if (
        state.product_selection is not None
        and state.product_selection.selected_product_ids
    ):
        return state.product_selection.selected_product_ids

    products = seller_repository.list_products(limit=max_products, offset=0)
    return [p.product_id for p in products]


def _build_competitor_narrative(overview: CompetitorOverviewOutput) -> str:
    """
    Deterministic narrative about competitor pricing.

    Later, this can be enriched by an LLM, but structure stays the same.
    """
    seller_avg = overview.seller_avg_price
    num = len(overview.competitors)

    if num == 0:
        return "No competitors found for this product in the warehouse snapshot."

    # Basic stats
    comp_prices = [c.competitor.price for c in overview.competitors]
    avg_comp_price = sum(comp_prices) / len(comp_prices)

    parts: List[str] = []
    parts.append(
        f"There are {num} competitors with average price {avg_comp_price:.2f}."
    )

    if seller_avg is None:
        parts.append(
            "Seller average price could not be computed due to missing sales data."
        )
    else:
        delta = avg_comp_price - seller_avg
        parts.append(f"Seller average price is {seller_avg:.2f}.")

        if abs(delta) < 0.01 * seller_avg:
            parts.append("Seller price is roughly in line with competitor average.")
        elif delta > 0:
            parts.append(
                "Competitors are generally priced higher than the seller; "
                "there may be room to increase price while remaining competitive."
            )
        else:
            parts.append(
                "Competitors are generally priced lower than the seller; "
                "seller may need to justify premium positioning or adjust price."
            )

    return " ".join(parts)


def update_competitor_analyses(
    state: SellerState,
    max_products: int = 10,
) -> SellerState:
    """
    Competitor Intelligence Agent.

    Responsibilities:
      - Select products to analyze
      - For each, gather competitor landscape via tools.competitor_tool
      - Populate SellerState.competitor_analyses with structured summaries
    """
    product_ids = _choose_product_ids_for_competitors(state, max_products=max_products)

    if not product_ids:
        logger.info("Competitor agent: no products to analyze")
        return state

    logger.info(
        "Competitor agent analyzing products",
        extra={"num_products": len(product_ids)},
    )

    existing_by_product: Dict[str, CompetitorAnalysis] = {
        a.product_id: a for a in state.competitor_analyses
    }
    updated_by_product: Dict[str, CompetitorAnalysis] = {}

    for product_id in product_ids:
        try:
            overview = get_competitor_overview(
                CompetitorOverviewInput(product_id=product_id)
            )
        except ValueError as exc:
            logger.warning(
                "Competitor agent: could not get overview for product",
                extra={"product_id": product_id, "error": str(exc)},
            )
            continue

        num_competitors = len(overview.competitors)
        avg_comp_price = (
            sum(c.competitor.price for c in overview.competitors) / num_competitors
            if num_competitors > 0
            else None
        )

        analysis = CompetitorAnalysis(
            product_id=product_id,
            num_competitors=num_competitors,
            avg_competitor_price=avg_comp_price,
            seller_avg_price=overview.seller_avg_price,
            price_positioning=_build_competitor_narrative(overview),
            notes="",
        )
        updated_by_product[product_id] = analysis

    merged: Dict[str, CompetitorAnalysis] = {
        **existing_by_product,
        **updated_by_product,
    }
    state.competitor_analyses = list(merged.values())

    logger.info(
        "Competitor agent updated competitor analyses",
        extra={"num_analyses": len(state.competitor_analyses)},
    )

    return state
