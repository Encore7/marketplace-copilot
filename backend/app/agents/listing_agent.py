from __future__ import annotations

from uuid import uuid4
from typing import List

from ..db import seller_repository
from ..observability.logging import get_logger
from ..tools.seo_tool import SEOEvaluationInput, evaluate_seo
from .state import ActionCategory, ActionItem, ActionPlan, ActionPriority, SellerState

logger = get_logger("agents.listing")


def update_listing_and_seo_actions(
    state: SellerState,
    marketplace: str = "amazon",
    max_products: int = 10,
) -> SellerState:
    """
    Listing & SEO Agent (initial deterministic version).

    Responsibilities:
      - For a subset of products:
          * fetch listing info from the warehouse
          * run SEOEvaluation via seo_tool
          * add action plan items based on issues/suggestions
    """
    # Choose products from sales analyses, or fallback to profile-based
    product_ids: List[str] = []
    if state.sales_analyses:
        product_ids = [a.product_id for a in state.sales_analyses][:max_products]

    if not product_ids:
        logger.info("Listing agent: no product ids derived from state; skipping")
        return state

    if not state.action_plan:
        state.action_plan = ActionPlan(
            overall_summary="",
            actions=[],
        )

    for product_id in product_ids:
        product = seller_repository.get_product(product_id)
        if product is None:
            continue

        title = product.title
        bullets: List[str] = []
        desc = ""

        # Very simple derived bullets from attributes for now.
        # Later we can store real bullets in warehouse.
        for key, value in product.attributes.items():
            bullets.append(f"{key}: {value}")

        seo_input = SEOEvaluationInput(
            product_id=product_id,
            marketplace=marketplace,
            title=title,
            bullets=bullets,
            description=desc,
        )

        result = evaluate_seo(seo_input)

        if result.score >= 80 and not result.issues:
            # Good enough, skip
            continue

        # Add one consolidated action per product
        issues_str = (
            "; ".join(result.issues) if result.issues else "General improvement"
        )
        action = ActionItem(
            id=f"listing-{product_id}-{uuid4().hex[:8]}",
            title=f"Improve listing SEO for product {product_id}",
            description=(
                f"SEO score is {result.score:.1f}/100. "
                f"Issues: {issues_str}. "
                "See individual suggestions for detailed improvements."
            ),
            category=ActionCategory.LISTING,
            priority=ActionPriority.MEDIUM,
            estimated_impact="medium",
            product_id=product_id,
        )

        state.action_plan.actions.append(action)

    logger.info(
        "Listing agent added listing/SEO actions",
        extra={"num_actions": len(state.action_plan.actions)},
    )

    return state
