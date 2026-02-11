from __future__ import annotations

from collections import Counter
from typing import List

from ..db import seller_repository
from ..observability.logging import get_logger
from .state import SellerProfile, SellerState

logger = get_logger("agents.profile")


def _compute_primary_categories(categories: List[str], top_k: int = 5) -> List[str]:
    """
    Compute the top-k primary categories by frequency.
    """
    counter = Counter(cat for cat in categories if cat)
    return [cat for cat, _ in counter.most_common(top_k)]


def update_seller_profile(state: SellerState) -> SellerState:
    """
    Seller Profile Agent.

    Responsibilities:
      - Aggregate basic stats from the seller warehouse:
          * total number of products
          * number of active listings
          * marketplaces in use
          * primary categories
      - Produce a concise, deterministic summary (no LLM yet).

    This agent does NOT read CSVs directly; it only talks to the
    warehouse via the seller_repository.
    """
    products = seller_repository.list_products(limit=10_000, offset=0)

    total_products = len(products)
    active_products = sum(1 for p in products if p.listing_status == "active")

    marketplaces_set = set()
    categories: List[str] = []

    for p in products:
        for m in p.marketplaces:
            marketplaces_set.add(m)
        if p.category:
            categories.append(p.category)

    marketplaces = sorted(marketplaces_set)
    primary_categories = _compute_primary_categories(categories)

    summary = (
        f"Seller currently has {total_products} products "
        f"({active_products} active listings) "
        f"across marketplaces: {', '.join(marketplaces) or 'none'}. "
        f"Primary categories: {', '.join(primary_categories) or 'not available'}."
    )

    state.seller_profile = SellerProfile(
        seller_id="seller-1",
        total_products=total_products,
        active_products=active_products,
        marketplaces=marketplaces,
        primary_categories=primary_categories,
        summary=summary,
    )

    logger.info(
        "Seller profile updated",
        extra={
            "seller_id": state.seller_profile.seller_id,
            "total_products": total_products,
            "active_products": active_products,
            "marketplaces": ",".join(marketplaces),
        },
    )

    return state
