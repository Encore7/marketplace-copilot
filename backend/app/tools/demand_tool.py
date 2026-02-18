from __future__ import annotations

from datetime import date, timedelta
from typing import List, Optional

from pydantic import BaseModel, Field

from ..db import seller_repository
from ..observability.llm_obs import traceable_node
from ..observability.logging import get_logger
from ..schemas.seller import SalesRecord

logger = get_logger("tools.demand")


class DemandForecastRequest(BaseModel):
    """
    Input for demand forecasting tool.
    """

    product_id: str
    horizon_days: int = Field(default=14, ge=1, le=90)
    history_window_days: int = Field(
        default=28,
        ge=7,
        le=365,
        description="How many past days to use for a simple moving-average forecast.",
    )


class DemandForecastPoint(BaseModel):
    """
    A single forecast point in time.
    """

    date: date
    expected_units: float = Field(ge=0)
    lower_ci: Optional[float] = Field(default=None, ge=0)
    upper_ci: Optional[float] = Field(default=None, ge=0)


class DemandForecastResponse(BaseModel):
    """
    Output of the demand forecast tool.
    """

    product_id: str
    horizon_days: int
    history_window_days: int
    forecast: List[DemandForecastPoint]


def _compute_moving_average(records: List[SalesRecord]) -> float:
    total_units = sum(r.units_sold for r in records)
    days_with_data = len({r.date for r in records})
    if days_with_data <= 0:
        return 0.0
    return total_units / days_with_data


@traceable_node("tool.demand")
def forecast_demand(input_data: DemandForecastRequest) -> DemandForecastResponse:
    """
    Tool: Compute a simple moving-average-based demand forecast.

    This is intentionally simple but production-friendly:
    - no heavy ML here
    - deterministic and explainable
    - agents can still call LLMs to explain/interpret this forecast
    """
    logger.info(
        "Running demand forecast",
        extra={
            "product_id": input_data.product_id,
            "horizon_days": input_data.horizon_days,
            "history_window_days": input_data.history_window_days,
        },
    )

    # We consider "today" as the latest date in the sales history (warehouse time).
    all_records = seller_repository.list_sales_history(
        product_id=input_data.product_id,
        start_date=None,
        end_date=None,
    )
    if not all_records:
        return DemandForecastResponse(
            product_id=input_data.product_id,
            horizon_days=input_data.horizon_days,
            history_window_days=input_data.history_window_days,
            forecast=[],
        )

    latest_date = max(r.date for r in all_records)
    history_start = latest_date - timedelta(days=input_data.history_window_days - 1)

    history_records = [
        r for r in all_records if r.date >= history_start and r.date <= latest_date
    ]

    avg_daily_units = _compute_moving_average(history_records)

    forecast_points: List[DemandForecastPoint] = []
    for i in range(1, input_data.horizon_days + 1):
        target_date = latest_date + timedelta(days=i)
        forecast_points.append(
            DemandForecastPoint(
                date=target_date,
                expected_units=avg_daily_units,
                lower_ci=None,
                upper_ci=None,
            )
        )

    return DemandForecastResponse(
        product_id=input_data.product_id,
        horizon_days=input_data.horizon_days,
        history_window_days=input_data.history_window_days,
        forecast=forecast_points,
    )
