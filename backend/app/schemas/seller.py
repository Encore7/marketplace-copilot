from __future__ import annotations

import json
from datetime import date
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator
from pydantic.config import ConfigDict


class Product(BaseModel):
    """
    Canonical representation of a product row from the seller warehouse.

    This model is aligned 1:1 with the columns in `products.csv`.
    It is also what tools / agents should use when reasoning about products.
    """

    model_config = ConfigDict(extra="ignore")

    product_id: str
    title: str
    brand: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    marketplaces: List[str]
    attributes: Dict[str, Any] = Field(default_factory=dict)
    image_quality_score: Optional[float] = None
    listing_status: Literal["active", "paused", "draft"]

    @field_validator("marketplaces", mode="before")
    @classmethod
    def parse_marketplaces(cls, value: Any) -> List[str]:
        """
        Parse marketplaces from CSV.

        Expected CSV formats:
        - JSON list string: '["amazon", "flipkart"]'
        - Comma-separated: 'amazon,flipkart'
        - Already a list: ["amazon", "flipkart"]
        """
        if value is None:
            return []

        if isinstance(value, list):
            return [str(v).strip() for v in value if str(v).strip()]

        if isinstance(value, str):
            text = value.strip()
            if not text:
                return []

            if text.startswith("["):
                try:
                    parsed = json.loads(text)
                    if isinstance(parsed, list):
                        return [str(v).strip() for v in parsed if str(v).strip()]
                except json.JSONDecodeError:
                    # Fall back to comma-separated
                    pass

            # Fallback: comma-separated string
            return [part.strip() for part in text.split(",") if part.strip()]

        # Fallback for unexpected types
        return [str(value).strip()]

    @field_validator("attributes", mode="before")
    @classmethod
    def parse_attributes(cls, value: Any) -> Dict[str, Any]:
        """
        Parse attributes from CSV.

        Expected CSV format:
        - JSON string: '{"gender":"men","size_range":"UK7-11"}'
        - Already a dict: {"gender": "men", "size_range": "UK7-11"}
        """
        if value is None:
            return {}

        if isinstance(value, dict):
            return value

        if isinstance(value, str):
            text = value.strip()
            if not text:
                return {}
            try:
                parsed = json.loads(text)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                return {}

        # Fallback: cannot parse to dict
        return {}


class CompetitorRecord(BaseModel):
    """
    Competitor data joined to a product from `competitors.csv`.

    This allows competitor-aware pricing, listing, and SEO analysis.
    """

    model_config = ConfigDict(extra="ignore")

    competitor_sku: str
    product_id: str
    platform: str
    title: str
    price: float = Field(ge=0)
    rating: Optional[float] = Field(default=None, ge=0, le=5)
    num_reviews: Optional[int] = Field(default=None, ge=0)
    main_features: Optional[str] = None
    fulfillment_type: Optional[str] = None


class InventoryRecord(BaseModel):
    """
    Inventory position for a product from `inventory.csv`.

    Used by inventory / demand tools to compute stock risk and reorder plans.
    """

    model_config = ConfigDict(extra="ignore")

    product_id: str
    stock_on_hand: int = Field(ge=0)
    reorder_level: int = Field(ge=0)
    lead_time_days: int = Field(ge=0)
    supplier_cost: float = Field(ge=0)


class ReviewRecord(BaseModel):
    """
    Customer reviews from `reviews.csv`.

    Enables sentiment, rating trends, and review-driven listing improvements.
    """

    model_config = ConfigDict(extra="ignore")

    review_id: str
    product_id: str
    rating: float = Field(ge=1, le=5)
    review_text: str
    date: date


class SalesRecord(BaseModel):
    """
    Daily/periodic sales data from `sales_history.csv`.

    Basis for demand forecasting, pricing impact, and profitability analysis.
    """

    model_config = ConfigDict(extra="ignore")

    date: date
    product_id: str
    marketplace: str
    units_sold: int = Field(ge=0)
    gross_revenue: float = Field(ge=0)
    price: float = Field(ge=0)
    returns: int = Field(ge=0)
    ad_spend: float = Field(ge=0)
    page_views: int = Field(ge=0)
