from __future__ import annotations

from ..observability.logging import get_logger
from ..tools.profit_tool import ProfitSimulationInput, simulate_profit
from .state import ActionItem, ActionPlan, SellerState

logger = get_logger("agents.profit")


def update_profit_summary(
    state: SellerState,
    marketplace: str = "amazon",
    max_products: int = 10,
) -> SellerState:
    """
    Profitability Agent (initial version).

    Responsibilities:
      - For a subset of products (from sales analyses):
          * simulate profit at current avg selling price
          * estimate overall margin health
      - Add a high-level profit-improvement action if warranted.
    """
    if not state.sales_analyses:
        logger.info("Profit agent: no sales analyses; skipping")
        return state

    total_revenue = 0.0
    weighted_profit = 0.0

    for a in state.sales_analyses[:max_products]:
        if a.avg_selling_price is None or a.total_units_sold <= 0:
            continue

        sim = simulate_profit(
            ProfitSimulationInput(
                product_id=a.product_id,
                marketplace=marketplace,
                candidate_price=a.avg_selling_price,
            )
        )

        revenue = a.total_units_sold * a.avg_selling_price
        total_revenue += revenue
        weighted_profit += revenue * (sim.margin_percent / 100.0)

    if total_revenue <= 0:
        logger.info("Profit agent: no meaningful revenue to evaluate; skipping")
        return state

    avg_margin_percent = (weighted_profit / total_revenue) * 100.0

    if not state.action_plan:
        state.action_plan = ActionPlan(
            overall_summary="",
            actions=[],
        )

    if avg_margin_percent < 10.0:
        title = "Improve overall profitability"
        description = (
            f"Estimated average profit margin across key products is "
            f"only ~{avg_margin_percent:.1f}%. "
            "Consider coordinated pricing, cost optimization, and ad efficiency changes."
        )
    else:
        title = "Monitor profitability trends"
        description = (
            f"Estimated average profit margin across key products is "
            f"~{avg_margin_percent:.1f}%. "
            "Maintain current strategy but monitor margins over time."
        )

    action = ActionItem(
        area="profitability",
        title=title,
        description=description,
        priority="high" if avg_margin_percent < 10.0 else "medium",
        impact="high",
        product_id=None,
    )

    state.action_plan.actions.append(action)

    logger.info(
        "Profit agent added profitability action",
        extra={"avg_margin_percent": avg_margin_percent},
    )

    return state
