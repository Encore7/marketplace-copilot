from __future__ import annotations

from typing import Dict
from typing import List

from ..observability.logging import get_logger
from .state import QueryContext, QueryMode, SellerState

logger = get_logger("agents.router")

_SUPPORTED_MARKETPLACES: List[str] = ["amazon", "flipkart", "meesho", "myntra"]
_INTENT_KEYS: List[str] = [
    "need_sales",
    "need_competitor",
    "need_inventory",
    "need_pricing",
    "need_profit",
    "need_listing_seo",
    "need_compliance",
    "need_rag",
]

_COMPLIANCE_TERMS = (
    "policy",
    "compliance",
    "restricted",
    "guideline",
    "image",
    "title",
    "seo",
    "citation",
)
_PRICING_TERMS = ("margin", "price", "profit", "competitor")
_INVENTORY_TERMS = ("stock", "stockout", "reorder", "demand")


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


def _empty_intents() -> Dict[str, bool]:
    return {key: False for key in _INTENT_KEYS}


def _capability_name(flag_key: str) -> str:
    return flag_key.replace("need_", "")


def _keyword_scores(raw_query: str) -> Dict[str, int]:
    text = (raw_query or "").lower()
    return {
        "compliance": sum(1 for term in _COMPLIANCE_TERMS if term in text),
        "pricing": sum(1 for term in _PRICING_TERMS if term in text),
        "inventory": sum(1 for term in _INVENTORY_TERMS if term in text),
    }


def _apply_mode_defaults(mode: QueryMode, intents: Dict[str, bool]) -> None:
    if mode == QueryMode.WEEKLY_PLAN:
        for k in intents:
            intents[k] = True
        return
    if mode == QueryMode.PRICING:
        intents["need_sales"] = True
        intents["need_competitor"] = True
        intents["need_pricing"] = True
        intents["need_profit"] = True
        return
    if mode == QueryMode.LISTING_SEO:
        intents["need_listing_seo"] = True
        intents["need_compliance"] = True
        intents["need_rag"] = True
        return
    if mode == QueryMode.INVENTORY:
        intents["need_inventory"] = True
        intents["need_sales"] = True
        return
    if mode == QueryMode.COMPLIANCE:
        intents["need_compliance"] = True
        intents["need_rag"] = True
        return
    if mode == QueryMode.PROFITABILITY:
        intents["need_sales"] = True
        intents["need_pricing"] = True
        intents["need_profit"] = True
        return

    # GENERAL_QA balanced default.
    intents["need_sales"] = True


def _apply_keyword_overlays(intents: Dict[str, bool], raw_query: str) -> Dict[str, int]:
    scores = _keyword_scores(raw_query)

    if scores["compliance"] > 0:
        intents["need_compliance"] = True
        intents["need_rag"] = True
        intents["need_listing_seo"] = True

    if scores["pricing"] > 0:
        intents["need_sales"] = True
        intents["need_competitor"] = True
        intents["need_pricing"] = True
        intents["need_profit"] = True

    if scores["inventory"] > 0:
        intents["need_inventory"] = True
        intents["need_sales"] = True

    return scores


def _routing_confidence(scores: Dict[str, int]) -> float:
    total = sum(scores.values())
    if total == 0:
        return 0.5
    return max(scores.values()) / total


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

    mode = state.query.mode or QueryMode.GENERAL_QA

    # Marketplaces: if provided, keep; else infer.
    marketplaces = state.query.marketplaces
    if not marketplaces:
        marketplaces = _infer_marketplaces_from_text(raw_query)

    intents = _empty_intents()
    _apply_mode_defaults(mode, intents)
    scores = _apply_keyword_overlays(intents, raw_query)
    confidence = _routing_confidence(scores)
    override_flag = state.query.fallback_override_flag

    # Balanced fallback: always keep core sales branch and add strongest targeted branch.
    if confidence < 0.6:
        intents["need_sales"] = True
        strongest = max(scores, key=scores.get)
        if strongest == "compliance" and scores[strongest] > 0:
            intents["need_rag"] = True
            intents["need_compliance"] = True
        elif strongest == "pricing" and scores[strongest] > 0:
            intents["need_competitor"] = True
            intents["need_pricing"] = True
            intents["need_profit"] = True
        elif strongest == "inventory" and scores[strongest] > 0:
            intents["need_inventory"] = True

    if override_flag and override_flag in intents:
        intents[override_flag] = True
        if override_flag == "need_compliance":
            intents["need_rag"] = True
        if override_flag == "need_pricing":
            intents["need_sales"] = True
            intents["need_competitor"] = True
            intents["need_profit"] = True
        if override_flag == "need_inventory":
            intents["need_sales"] = True

    requested_capabilities = [
        _capability_name(k) for k, enabled in intents.items() if enabled
    ]

    state.query = QueryContext(
        raw_query=raw_query,
        mode=mode,  # resolved mode is deterministic for now
        marketplaces=marketplaces,
        language=state.query.language,
        session_id=state.query.session_id,
        seller_id=state.query.seller_id,
        seller_name=state.query.seller_name,
        memory_facts=state.query.memory_facts,
        recent_chat_turns=state.query.recent_chat_turns,
        requested_capabilities=requested_capabilities,
        intent_flags=intents,
        routing_confidence=confidence,
        fallback_override_flag=override_flag,
    )

    logger.info(
        "Router agent updated query context",
        extra={
            "mode": state.query.mode.value,
            "marketplaces": ",".join(state.query.marketplaces),
            "requested_capabilities": ",".join(state.query.requested_capabilities),
            "routing_confidence": state.query.routing_confidence,
        },
    )

    return state
