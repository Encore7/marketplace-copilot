from __future__ import annotations

import json
from datetime import date
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


# Product
class Product(BaseModel):
    product_id: str
    title: str
    brand: Optional[str]
    category: Optional[str]
    subcategory: Optional[str]
    marketplaces: List[str]
    attributes: Dict[str, Any]
    image_quality_score: Optional[float] = None
    listing_status: Literal["active", "paused", "draft"]

    @field_validator("marketplaces", mode="before")
    @classmethod
    def parse_marketplaces(cls, value):
        # If CSV contains string like '["amazon", "flipkart"]'
        if isinstance(value, str):
            return json.loads(value)
        return value

    @field_validator("attributes", mode="before")
    @classmethod
    def parse_attributes(cls, value):
        # For CSV: '{"gender":"men","size_range":"UK7-11"}'
        if isinstance(value, str):
            return json.loads(value)
        return value


# CompetitorRecord
class CompetitorRecord(BaseModel):
    competitor_sku: str
    product_id: str
    platform: str
    title: str
    price: float = Field(ge=0)
    rating: Optional[float] = Field(default=None, ge=0, le=5)
    num_reviews: Optional[int] = Field(default=None, ge=0)
    main_features: Optional[str] = None
    fulfillment_type: Optional[str] = None


# InventoryRecord
class InventoryRecord(BaseModel):
    product_id: str
    stock_on_hand: int = Field(ge=0)
    reorder_level: int = Field(ge=0)
    lead_time_days: int = Field(ge=0)
    supplier_cost: float = Field(ge=0)


# ReviewRecord
class ReviewRecord(BaseModel):
    review_id: str
    product_id: str
    rating: float = Field(ge=1, le=5)
    review_text: str
    date: date


# SalesRecord
class SalesRecord(BaseModel):
    date: date
    product_id: str
    marketplace: str
    units_sold: int = Field(ge=0)
    gross_revenue: float = Field(ge=0)
    price: float = Field(ge=0)
    returns: int = Field(ge=0)
    ad_spend: float = Field(ge=0)
    page_views: int = Field(ge=0)


# RAGChunk
class RAGChunk(BaseModel):
    id: str
    text: str
    marketplace: str
    section: str
    source: str
    score: Optional[float] = None
