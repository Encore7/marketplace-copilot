from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    query: str = Field(..., description="Natural language request from seller.")
    product_ids: Optional[List[str]] = Field(
        default=None,
        description="Optional explicit subset of products to focus on.",
    )
