from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class ActionItem(BaseModel):
    type: str
    product_id: str
    priority: str
    message: str


class AnalyzeResponse(BaseModel):
    mode: Optional[str]
    actions: List[ActionItem]
    markdown: str
    raw_state: Dict[str, Any]
