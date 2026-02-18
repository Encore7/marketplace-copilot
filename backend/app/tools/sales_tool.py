from __future__ import annotations

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field

from ..db import seller_repository
from ..observability.llm_obs import traceable_node
from ..observability.logging import get_logger
from ..schemas.seller import Product, SalesRecord

logger = get_logger("tools.sales")


class SalesTimeSeriesPoint(BaseModel):
    """
    A single point in the sales time series for a product.
    """

    date: date
    units_sold: int
    gross_revenue: float
    returns: int
    ad_spend: float
    page_views: int


class SalesSummary(BaseModel):
    """
    Aggregated sales metrics for a product over a given period.
    """

    total_units_sold: int = Field(ge=0)
    total_gross_revenue: float = Field(ge=0)
    total_returns: int = Field(ge=0)
    total_ad_spend: float = Field(ge=0)
    total_page_views: int = Field(ge=0)

    avg_selling_price: Optional[float] = Field(default=None, ge=0)
    conversion_rate: Optional[float] = Field(default=None, ge=0, le=1)


class ProductSalesOverviewInput(BaseModel):
    """
    Input for retrieving product + sales overview.
    """

    product_id: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class ProductSalesOverviewOutput(BaseModel):
    """
    Output combining product metadata, aggregated sales, and time series.
    """

    product: Product
    summary: SalesSummary
    timeseries: List[SalesTimeSeriesPoint]


def _summarize_sales(records: List[SalesRecord]) -> SalesSummary:
    total_units = sum(r.units_sold for r in records)
    total_revenue = sum(r.gross_revenue for r in records)
    total_returns = sum(r.returns for r in records)
    total_ad_spend = sum(r.ad_spend for r in records)
    total_page_views = sum(r.page_views for r in records)

    if total_units > 0:
        avg_price = total_revenue / total_units
    else:
        avg_price = None

    if total_page_views > 0:
        conversion = total_units / total_page_views
    else:
        conversion = None

    return SalesSummary(
        total_units_sold=total_units,
        total_gross_revenue=total_revenue,
        total_returns=total_returns,
        total_ad_spend=total_ad_spend,
        total_page_views=total_page_views,
        avg_selling_price=avg_price,
        conversion_rate=conversion,
    )


def _to_timeseries(records: List[SalesRecord]) -> List[SalesTimeSeriesPoint]:
    return [
        SalesTimeSeriesPoint(
            date=r.date,
            units_sold=r.units_sold,
            gross_revenue=r.gross_revenue,
            returns=r.returns,
            ad_spend=r.ad_spend,
            page_views=r.page_views,
        )
        for r in records
    ]


@traceable_node("tool.sales")
def get_product_sales_overview(
    input_data: ProductSalesOverviewInput,
) -> ProductSalesOverviewOutput:
    """
    Tool: Fetch product metadata + sales history and compute summary metrics.

    Agents can use this to:
      - understand volume, revenue, returns
      - reason about pricing changes, demand, and listing performance
    """
    logger.info(
        "Fetching product sales overview",
        extra={"product_id": input_data.product_id},
    )

    product = seller_repository.get_product(input_data.product_id)
    if product is None:
        raise ValueError(f"Product {input_data.product_id} not found in warehouse")

    records = seller_repository.list_sales_history(
        product_id=input_data.product_id,
        start_date=input_data.start_date,
        end_date=input_data.end_date,
    )

    summary = _summarize_sales(records)
    timeseries = _to_timeseries(records)

    return ProductSalesOverviewOutput(
        product=product,
        summary=summary,
        timeseries=timeseries,
    )
