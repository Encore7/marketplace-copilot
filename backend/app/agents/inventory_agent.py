from __future__ import annotations

from datetime import date
from typing import Dict, List, Optional

from ..db import seller_repository
from ..observability.logging import get_logger
from ..tools.demand_tool import (
    DemandForecastRequest,
    DemandForecastResponse,
    forecast_demand,
)
from .state import InventoryAnalysis, InventoryRiskLevel, SellerState

logger = get_logger("agents.inventory")


def _choose_product_ids_for_inventory(
    state: SellerState,
    max_products: int = 10,
) -> List[str]:
    """
    Decide which products should be analyzed for inventory risk.

    Priority:
      1) ProductSelection.selected_product_ids
      2) Fallback catalog slice
    """
    if (
        state.product_selection is not None
        and state.product_selection.selected_product_ids
    ):
        return state.product_selection.selected_product_ids

    products = seller_repository.list_products(limit=max_products, offset=0)
    return [p.product_id for p in products]


def _compute_days_of_cover(
    current_stock: int,
    forecast: DemandForecastResponse,
) -> Optional[float]:
    """
    Approximate how many days of demand the current stock can cover.

    We use average expected_units across the horizon as a proxy.
    """
    if current_stock <= 0 or not forecast.forecast:
        return None

    avg_daily = sum(pt.expected_units for pt in forecast.forecast) / len(
        forecast.forecast
    )
    if avg_daily <= 0:
        return None

    return current_stock / avg_daily


def _classify_risk(
    days_of_cover: Optional[float],
    reorder_level: int,
    current_stock: int,
) -> InventoryRiskLevel:
    """
    Simple rule-based risk classification.
    """
    if days_of_cover is None:
        # If we don't know demand, fall back to stock vs reorder_level
        if current_stock <= 0:
            return InventoryRiskLevel.CRITICAL
        if current_stock <= reorder_level:
            return InventoryRiskLevel.HIGH
        return InventoryRiskLevel.MEDIUM

    if days_of_cover < 3:
        return InventoryRiskLevel.CRITICAL
    if days_of_cover < 7:
        return InventoryRiskLevel.HIGH
    if days_of_cover < 14:
        return InventoryRiskLevel.MEDIUM
    return InventoryRiskLevel.LOW


def _build_inventory_narrative(
    days_of_cover: Optional[float],
    risk_level: InventoryRiskLevel,
    current_stock: int,
    reorder_level: int,
) -> str:
    """
    Build a deterministic narrative about stock risk.
    """
    parts: List[str] = []

    parts.append(f"Current stock: {current_stock}, reorder level: {reorder_level}. ")

    if days_of_cover is None:
        parts.append(
            "Demand forecast is too uncertain to compute days of cover; "
            "risk is estimated primarily from stock vs reorder level. "
        )
    else:
        parts.append(f"Estimated days of cover: {days_of_cover:.1f}. ")

    if risk_level == InventoryRiskLevel.CRITICAL:
        parts.append(
            "Risk level is CRITICAL: immediate attention is required to avoid stockout."
        )
    elif risk_level == InventoryRiskLevel.HIGH:
        parts.append(
            "Risk level is HIGH: stock may run out soon; consider expediting replenishment."
        )
    elif risk_level == InventoryRiskLevel.MEDIUM:
        parts.append("Risk level is MEDIUM: monitor stock and replenishment closely.")
    else:
        parts.append(
            "Risk level is LOW: current stock appears sufficient for the near term."
        )

    return " ".join(parts)


def update_inventory_analyses(
    state: SellerState,
    max_products: int = 10,
    forecast_horizon_days: int = 14,
    history_window_days: int = 28,
) -> SellerState:
    """
    Inventory & Demand Agent.

    Responsibilities:
      - Select products
      - For each product:
          * fetch inventory record
          * run demand_tool.forecast_demand
          * compute projected days of cover
          * assign a qualitative risk level
      - Populate SellerState.inventory_analyses
    """
    product_ids = _choose_product_ids_for_inventory(state, max_products=max_products)

    if not product_ids:
        logger.info("Inventory agent: no products to analyze")
        return state

    logger.info(
        "Inventory agent analyzing products",
        extra={"num_products": len(product_ids)},
    )

    existing_by_product: Dict[str, InventoryAnalysis] = {
        a.product_id: a for a in state.inventory_analyses
    }
    updated_by_product: Dict[str, InventoryAnalysis] = {}

    for product_id in product_ids:
        inv = seller_repository.get_inventory(product_id)
        if inv is None:
            logger.warning(
                "Inventory agent: no inventory record found for product",
                extra={"product_id": product_id},
            )
            continue

        forecast = forecast_demand(
            DemandForecastRequest(
                product_id=product_id,
                horizon_days=forecast_horizon_days,
                history_window_days=history_window_days,
            )
        )

        days_of_cover = _compute_days_of_cover(
            current_stock=inv.stock_on_hand,
            forecast=forecast,
        )

        risk_level = _classify_risk(
            days_of_cover=days_of_cover,
            reorder_level=inv.reorder_level,
            current_stock=inv.stock_on_hand,
        )

        analysis = InventoryAnalysis(
            product_id=product_id,
            current_stock=inv.stock_on_hand,
            reorder_level=inv.reorder_level,
            projected_days_of_cover=days_of_cover,
            risk_level=risk_level,
            narrative=_build_inventory_narrative(
                days_of_cover=days_of_cover,
                risk_level=risk_level,
                current_stock=inv.stock_on_hand,
                reorder_level=inv.reorder_level,
            ),
        )

        updated_by_product[product_id] = analysis

    merged: Dict[str, InventoryAnalysis] = {
        **existing_by_product,
        **updated_by_product,
    }
    state.inventory_analyses = list(merged.values())

    logger.info(
        "Inventory agent updated inventory analyses",
        extra={"num_analyses": len(state.inventory_analyses)},
    )

    return state
