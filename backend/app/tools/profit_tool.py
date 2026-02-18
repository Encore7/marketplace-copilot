from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Dict, List

import yaml
from pydantic import BaseModel, Field

from ..db import seller_repository
from ..observability.llm_obs import traceable_node
from ..observability.logging import get_logger

logger = get_logger("tools.profit")


class FeeConfig(BaseModel):
    referral_fee_percent: float = 0.0
    closing_fee_flat: float = 0.0
    fba_pick_pack_fee: float = 0.0
    storage_fee_per_unit: float = 0.0
    return_handling_fee: float = 0.0
    payment_gateway_fee_percent: float = 0.0


class FeeComponent(BaseModel):
    name: str
    amount_per_unit: float


class ProfitSimulationInput(BaseModel):
    product_id: str
    marketplace: str
    candidate_price: float = Field(gt=0.0)


class ProfitSimulationOutput(BaseModel):
    product_id: str
    marketplace: str
    candidate_price: float
    supplier_cost: float
    total_fees_per_unit: float
    profit_per_unit: float
    margin_percent: float
    fee_breakdown: List[FeeComponent]


@lru_cache()
def _load_fee_configs() -> Dict[str, FeeConfig]:
    """
    Load fee configuration from config/fees.yaml once.

    Structure expected:
      amazon:
        default:
          referral_fee_percent: ...
          ...
    """
    config_path = Path(__file__).resolve().parents[3] / "config" / "fees.yaml"
    if not config_path.exists():
        logger.warning("fees.yaml not found; using zero fees")
        return {}

    with config_path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    configs: Dict[str, FeeConfig] = {}
    for marketplace, tiers in raw.items():
        default_cfg = tiers.get("default") if isinstance(tiers, dict) else {}
        try:
            configs[marketplace] = FeeConfig.model_validate(default_cfg)
        except Exception as exc:
            logger.warning(
                "Failed to parse fee config for marketplace",
                extra={"marketplace": marketplace, "error": str(exc)},
            )
    return configs


def _get_fee_config(marketplace: str) -> FeeConfig:
    configs = _load_fee_configs()
    cfg = configs.get(marketplace)
    if cfg is None:
        logger.warning(
            "No fee config found for marketplace; using zero fees",
            extra={"marketplace": marketplace},
        )
        return FeeConfig()
    return cfg


@traceable_node("tool.profit")
def simulate_profit(input_data: ProfitSimulationInput) -> ProfitSimulationOutput:
    """
    Tool: simulate per-unit profit and margin for a candidate price.

    Uses:
      - Inventory.supplier_cost from warehouse
      - fees.yaml for marketplace fee assumptions
    """
    inv = seller_repository.get_inventory(input_data.product_id)
    supplier_cost = inv.supplier_cost if inv is not None else 0.0

    fee_cfg = _get_fee_config(input_data.marketplace)

    referral_fee = input_data.candidate_price * fee_cfg.referral_fee_percent / 100.0
    payment_gateway_fee = (
        input_data.candidate_price * fee_cfg.payment_gateway_fee_percent / 100.0
    )

    fee_breakdown = [
        FeeComponent(name="referral_fee", amount_per_unit=referral_fee),
        FeeComponent(name="closing_fee", amount_per_unit=fee_cfg.closing_fee_flat),
        FeeComponent(name="pick_pack_fee", amount_per_unit=fee_cfg.fba_pick_pack_fee),
        FeeComponent(name="storage_fee", amount_per_unit=fee_cfg.storage_fee_per_unit),
        FeeComponent(
            name="return_handling_fee",
            amount_per_unit=fee_cfg.return_handling_fee,
        ),
        FeeComponent(
            name="payment_gateway_fee",
            amount_per_unit=payment_gateway_fee,
        ),
    ]

    total_fees = sum(c.amount_per_unit for c in fee_breakdown)
    profit_per_unit = input_data.candidate_price - supplier_cost - total_fees
    margin_percent = (
        (profit_per_unit / input_data.candidate_price) * 100.0
        if input_data.candidate_price > 0
        else 0.0
    )

    return ProfitSimulationOutput(
        product_id=input_data.product_id,
        marketplace=input_data.marketplace,
        candidate_price=input_data.candidate_price,
        supplier_cost=supplier_cost,
        total_fees_per_unit=total_fees,
        profit_per_unit=profit_per_unit,
        margin_percent=margin_percent,
        fee_breakdown=fee_breakdown,
    )
