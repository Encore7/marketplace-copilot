from __future__ import annotations

from typing import List, Optional

from ..observability.logging import get_logger
from ..tools.profit_tool import ProfitSimulationInput, simulate_profit
from .state import ActionItem, ActionPlan, SellerState

logger = get_logger("agents.pricing")


def _get_avg_selling_price_for_product(
    state: SellerState, product_id: str
) -> Optional[float]:
    for a in state.sales_analyses:
        if a.product_id == product_id and a.avg_selling_price is not None:
            return a.avg_selling_price
    return None


def _get_price_anchor(state: SellerState, product_id: str) -> Optional[float]:
    """
    Use competitor data as a price anchor if available; otherwise
    fall back to avg selling price.
    """
    for c in state.competitor_analyses:
        if c.product_id == product_id and c.avg_competitor_price is not None:
            return c.avg_competitor_price

    return _get_avg_selling_price_for_product(state, product_id)


def _choose_recommended_price(
    current_price: float,
    anchor_price: Optional[float],
) -> float:
    """
    Simple heuristic:

      - If we have a competitor anchor:
          * if seller << anchor -> +5%
          * if seller >> anchor -> -5%
          * else -> keep same
      - Else: keep same.
    """
    if anchor_price is None or current_price <= 0:
        return current_price

    if current_price < 0.9 * anchor_price:
        return current_price * 1.05
    if current_price > 1.1 * anchor_price:
        return current_price * 0.95
    return current_price


def update_pricing_recommendations(
    state: SellerState,
    marketplace: str = "amazon",
    max_products: int = 10,
) -> SellerState:
    """
    Pricing Optimization Agent (initial heuristic version).

    Responsibilities:
      - For a subset of products:
          * derive a current price (avg selling price)
          * propose a small price adjustment based on competitor anchors
          * simulate profit using profit_tool
      - Push resulting recommendations as ActionItems in state.action_plan.
    """
    if not state.sales_analyses:
        logger.info("Pricing agent: no sales analyses available; skipping")
        return state

    product_ids = [a.product_id for a in state.sales_analyses][:max_products]

    if not state.action_plan:
        state.action_plan = ActionPlan(
            overall_summary="",
            actions=[],
        )

    for product_id in product_ids:
        current_price = _get_avg_selling_price_for_product(state, product_id)
        if current_price is None or current_price <= 0:
            continue

        anchor_price = _get_price_anchor(state, product_id)
        recommended_price = _choose_recommended_price(current_price, anchor_price)

        sim = simulate_profit(
            ProfitSimulationInput(
                product_id=product_id,
                marketplace=marketplace,
                candidate_price=recommended_price,
            )
        )

        # Only create an action if margin is positive or improved.
        rationale_parts: List[str] = []
        rationale_parts.append(
            f"Simulated margin at {recommended_price:.2f} is "
            f"{sim.margin_percent:.2f}% per unit."
        )
        if anchor_price is not None:
            rationale_parts.append(f"Competitor average price is {anchor_price:.2f}.")

        rationale = " ".join(rationale_parts)

        action = ActionItem(
            area="pricing",
            title=f"Adjust price for product {product_id}",
            description=(
                f"Current avg selling price is ~{current_price:.2f}. "
                f"Recommended price: {recommended_price:.2f}. {rationale}"
            ),
            priority="medium",
            impact="medium",
            product_id=product_id,
        )

        state.action_plan.actions.append(action)

    logger.info(
        "Pricing agent added pricing actions",
        extra={"num_actions": len(state.action_plan.actions)},
    )

    return state
