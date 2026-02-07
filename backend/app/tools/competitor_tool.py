from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

from ..db import seller_repository
from ..observability.logging import get_logger
from ..schemas.seller import CompetitorRecord, Product, SalesRecord

logger = get_logger("tools.competitor")


class CompetitorWithDelta(BaseModel):
    """
    Competitor record enriched with simple price deltas
    vs. the seller's observed average selling price.
    """

    competitor: CompetitorRecord
    seller_avg_price: Optional[float] = Field(default=None, ge=0)
    price_delta: Optional[float] = Field(
        default=None,
        description="competitor.price - seller_avg_price",
    )


class CompetitorOverviewInput(BaseModel):
    """
    Input for competitor overview tool.
    """

    product_id: str


class CompetitorOverviewOutput(BaseModel):
    """
    Combined view of the product and its competitors.
    """

    product: Product
    seller_avg_price: Optional[float]
    competitors: List[CompetitorWithDelta]


def _compute_seller_avg_price(sales_records: List[SalesRecord]) -> Optional[float]:
    total_units = sum(r.units_sold for r in sales_records)
    total_revenue = sum(r.gross_revenue for r in sales_records)
    if total_units <= 0:
        return None
    return total_revenue / total_units


def get_competitor_overview(
    input_data: CompetitorOverviewInput,
) -> CompetitorOverviewOutput:
    """
    Tool: Retrieve product + competitors and compute basic price deltas.

    This is enough for an agent to reason about:
      - Undercutting / overpricing vs. competition
      - Which competitors are closest in price
    """
    logger.info(
        "Fetching competitor overview",
        extra={"product_id": input_data.product_id},
    )

    product = seller_repository.get_product(input_data.product_id)
    if product is None:
        raise ValueError(f"Product {input_data.product_id} not found in warehouse")

    competitors = seller_repository.list_competitors(input_data.product_id)
    sales_records = seller_repository.list_sales_history(
        product_id=input_data.product_id,
        start_date=None,
        end_date=None,
    )

    seller_avg_price = _compute_seller_avg_price(sales_records)

    enriched: List[CompetitorWithDelta] = []
    for comp in competitors:
        if seller_avg_price is not None:
            price_delta = comp.price - seller_avg_price
        else:
            price_delta = None
        enriched.append(
            CompetitorWithDelta(
                competitor=comp,
                seller_avg_price=seller_avg_price,
                price_delta=price_delta,
            )
        )

    return CompetitorOverviewOutput(
        product=product,
        seller_avg_price=seller_avg_price,
        competitors=enriched,
    )
