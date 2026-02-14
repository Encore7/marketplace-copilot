from __future__ import annotations

from typing import List

from ..observability.logging import get_logger
from .state import QueryContext, QueryMode, SellerState

logger = get_logger("agents.router")

_SUPPORTED_MARKETPLACES: List[str] = ["amazon", "flipkart", "meesho", "myntra"]


def _infer_marketplaces_from_text(text: str) -> List[str]:
    """
    Very simple heuristic to infer marketplaces from the raw query text.
    """
    text_lower = text.lower()
    markets: List[str] = []

    for m in _SUPPORTED_MARKETPLACES:
        if m in text_lower:
            markets.append(m)

    # If none found, default to "all marketplaces"
    if not markets:
        markets = list(_SUPPORTED_MARKETPLACES)
    return markets


def update_query_routing(state: SellerState) -> SellerState:
    """
    Router Agent.

    Responsibilities:
      - Ensure `state.query` is populated.
      - Choose a reasonable mode (for now, default GENERAL_QA unless explicitly set).
      - Infer marketplaces from the query text if not provided.

    This is deliberately lightweight and deterministic. If we need a more
    advanced router later, we can replace this with an LLM-based classifier.
    """
    if state.query is None:
        raise ValueError(
            "RouterAgent: state.query is missing; initial state is malformed."
        )

    raw_query = state.query.raw_query or ""

    # Mode: if caller supplied one, keep it; else default.
    mode = state.query.mode or QueryMode.GENERAL_QA

    # Marketplaces: if provided, keep; else infer.
    marketplaces = state.query.marketplaces
    if not marketplaces:
        marketplaces = _infer_marketplaces_from_text(raw_query)

    state.query = QueryContext(
        raw_query=raw_query,
        mode=mode,
        marketplaces=marketplaces,
        language=state.query.language,
    )

    logger.info(
        "Router agent updated query context",
        extra={
            "mode": state.query.mode.value,
            "marketplaces": ",".join(state.query.marketplaces),
        },
    )

    return state
