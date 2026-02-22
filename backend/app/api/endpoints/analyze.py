from __future__ import annotations

import re
import time
from uuid import uuid4
from typing import Any, Dict, List, Optional, Set

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from pydantic.config import ConfigDict

from ...agents.graph import create_copilot_graph
from ...agents.state import (
    Critique,
    FinalAnswer,
    HITLFeedback,
    QueryContext,
    QueryMode,
    SellerState,
)
from ...db.chat_store import (
    add_message,
    create_session,
    ensure_session,
    get_memory_facts,
    get_recent_turns,
    upsert_memory_fact,
)
from ...observability.domain_metrics import (
    copilot_request_latency_seconds,
    copilot_requests_total,
)
from ...observability.llm_obs import traceable_node
from ...observability.logging import get_logger

logger = get_logger("api.analyze")

router = APIRouter(tags=["analyze"])

# Compile the LangGraph once at import time.
_copilot_graph = create_copilot_graph()

# Pydantic request/response models for the endpoint


class AnalyzeRequest(BaseModel):
    """
    Request payload for the copilot analyze endpoint.

    This is intentionally minimal; downstream agents + tools will
    fetch all additional data they need from the warehouse and RAG.
    """

    model_config = ConfigDict(extra="ignore")

    query: str = Field(
        ...,
        description="Natural-language question or request from the seller.",
    )
    mode: Optional[QueryMode] = Field(
        default=None,
        description=(
            "Optional explicit mode for the copilot. "
            "If omitted, the router will choose a default."
        ),
    )
    marketplaces: List[str] = Field(
        default_factory=list,
        description="Optional list of marketplaces in scope (amazon, flipkart, etc.).",
    )
    language: str = Field(
        default="en",
        description="Language of the query (for future localization).",
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Persistent chat thread/session id for multi-turn context.",
    )
    seller_id: Optional[str] = Field(
        default=None,
        description="Logical seller id for session scoping.",
    )
    seller_name: Optional[str] = Field(
        default=None,
        description="Seller name to persist and use in subsequent turns.",
    )


class AnalyzeResponse(BaseModel):
    """
    Response payload for the copilot analyze endpoint.

    We return:
      - final_answer: user-facing markdown + structured action plan
      - critique: LLM-based reflection on the plan (optional)
      - hitl_feedback: container that can later be populated with user feedback
      - state: the final SellerState (useful for debugging / evals)
    """

    model_config = ConfigDict(extra="ignore")

    final_answer: FinalAnswer
    critique: Optional[Critique] = None
    hitl_feedback: Optional[HITLFeedback] = None
    execution_trace: List[str] = Field(default_factory=list)
    used_tools: List[str] = Field(
        default_factory=list,
        description="Unique tool identifiers used during this run.",
    )
    used_rag_evidence: List[str] = Field(
        default_factory=list,
        description=(
            "Evidence references from retrieved RAG chunks in the form "
            "'marketplace:section:source'."
        ),
    )
    rag_debug: Optional[Dict[str, Any]] = Field(
        default=None,
        description=(
            "RAG retrieval debug metadata (backend/mode/fusion/chunk_count) "
            "to make retrieval strategy explicit."
        ),
    )
    routing_debug: Optional[Dict[str, Any]] = Field(
        default=None,
        description=(
            "Routing debug metadata: intent flags, active/skipped branches, "
            "requested capabilities, and confidence."
        ),
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Session/thread identifier used for this analyze run.",
    )
    request_id: Optional[str] = Field(
        default=None,
        description="Request identifier for traceability across chat messages.",
    )
    state: SellerState


# Internal helpers


def _build_initial_state(
    req: AnalyzeRequest,
    session_id: Optional[str],
    memory_facts: List[str],
    recent_turns: List[str],
    remembered_seller_name: Optional[str],
) -> Dict[str, Any]:
    """
    Construct the initial SellerState (as a dict) for the LangGraph run.
    """
    query_ctx = QueryContext(
        raw_query=req.query,
        mode=req.mode or QueryMode.GENERAL_QA,
        marketplaces=req.marketplaces,
        language=req.language,
        session_id=session_id,
        seller_id=req.seller_id,
        seller_name=req.seller_name or remembered_seller_name,
        memory_facts=memory_facts,
        recent_chat_turns=recent_turns,
    )

    state = SellerState(
        query=query_ctx,
    )

    return state.model_dump()


def _mode_label_from_state(state: SellerState) -> str:
    """
    Derive a stable mode label for metrics from the final state (or fallback).
    """
    if state.query and state.query.mode:
        return state.query.mode.value
    return "unknown"


def _extract_used_tools(execution_trace: List[str]) -> List[str]:
    tools: Set[str] = set()
    for item in execution_trace:
        if "tools=" not in item:
            continue
        tools_str = item.split("tools=", 1)[1].strip()
        for tool in tools_str.split(","):
            cleaned = tool.strip()
            if cleaned:
                tools.add(cleaned)
    return sorted(tools)


def _extract_rag_evidence(state: SellerState, max_items: int = 10) -> List[str]:
    if state.rag_context is None:
        return []

    out: List[str] = []
    seen: Set[str] = set()
    for chunk in state.rag_context.chunks:
        ref = (
            f"{chunk.marketplace or 'any'}:"
            f"{chunk.section or 'unknown_section'}:"
            f"{chunk.source or 'unknown_source'}"
        )
        if ref in seen:
            continue
        seen.add(ref)
        out.append(ref)
        if len(out) >= max_items:
            break
    return out


def _build_rag_debug(state: SellerState) -> Optional[Dict[str, Any]]:
    if state.rag_context is None:
        return None

    mode = state.rag_context.retrieval_mode
    return {
        "backend": state.rag_context.backend,
        "mode": mode,
        "strategy": (
            "lexical+vector_rrf"
            if mode == "hybrid"
            else ("vector_only" if mode == "vector" else "lexical_only")
        ),
        "fusion_method": state.rag_context.fusion_method,
        "chunk_count": len(state.rag_context.chunks),
    }


def _build_routing_debug(state: SellerState) -> Optional[Dict[str, Any]]:
    if state.query is None:
        return None
    return {
        "mode": state.query.mode.value,
        "requested_capabilities": state.query.requested_capabilities,
        "intent_flags": state.query.intent_flags,
        "routing_confidence": state.query.routing_confidence,
        "active_branches": state.active_branches,
        "skipped_branches": state.skipped_branches,
        "fallback_applied": bool(state.answer_quality_signals.get("fallback_applied", 0.0)),
        "fallback_branch": (
            state.query.fallback_override_flag
            if state.query.fallback_override_flag
            else None
        ),
    }


def _should_apply_fallback(query_text: str, state: SellerState) -> bool:
    if state.query is None:
        return False
    if state.answer_quality_signals.get("fallback_applied", 0.0) >= 1.0:
        return False

    low_confidence = state.query.routing_confidence < 0.6
    weak_actions = (
        state.action_plan is None
        or len(state.action_plan.actions) < 2
    )
    needs_citations = "citation" in query_text.lower() or "cite" in query_text.lower()
    weak_rag = needs_citations and (state.rag_context is None or not state.rag_context.chunks)
    return low_confidence and (weak_actions or weak_rag)


def _pick_fallback_flag(query_text: str, state: SellerState) -> Optional[str]:
    if state.query is None:
        return None
    intents = state.query.intent_flags or {}
    q = query_text.lower()

    compliance_terms = ("policy", "compliance", "restricted", "guideline", "image", "title", "seo", "citation", "cite")
    pricing_terms = ("margin", "price", "profit", "competitor")
    inventory_terms = ("stock", "stockout", "reorder", "demand")

    if any(t in q for t in compliance_terms) and not intents.get("need_compliance", False):
        return "need_compliance"
    if any(t in q for t in pricing_terms) and not intents.get("need_pricing", False):
        return "need_pricing"
    if any(t in q for t in inventory_terms) and not intents.get("need_inventory", False):
        return "need_inventory"
    if not intents.get("need_compliance", False):
        return "need_compliance"
    if not intents.get("need_pricing", False):
        return "need_pricing"
    if not intents.get("need_inventory", False):
        return "need_inventory"
    return None


@traceable_node("api.analyze.graph_run")
async def _run_graph_with_trace(
    initial_state: Dict[str, Any],
    session_id: Optional[str],
    request_id: str,
) -> Dict[str, Any]:
    return await _copilot_graph.ainvoke(initial_state)


def _extract_seller_name_from_text(text: str) -> Optional[str]:
    pattern = r"\b(?:my name is|i am|i'm)\s+([A-Za-z][A-Za-z\s'-]{1,60})\b"
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        return None
    name = " ".join(match.group(1).strip().split())
    return name[:64] if name else None


# Endpoint


@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
    summary="Analyze seller account and return recommendations.",
)
async def analyze(req: AnalyzeRequest) -> AnalyzeResponse:
    """
    Main copilot endpoint.

    Flow:
      1. Build initial SellerState from request.
      2. Invoke LangGraph with that state.
      3. Validate / normalize final state as SellerState.
      4. Return FinalAnswer + full state.

    Observability:
      - Domain metrics (requests + latency per mode)
      - JSON logs with trace/span from logging factory
    """
    start_time = time.perf_counter()
    requested_mode_label = req.mode.value if req.mode else "auto"

    copilot_requests_total.labels(mode=requested_mode_label).inc()

    logger.info(
        "Analyze request received",
        extra={
            "requested_mode": requested_mode_label,
            "marketplaces": ",".join(req.marketplaces),
        },
    )

    session_id: Optional[str] = None
    request_id = uuid4().hex
    fallback_applied = False
    fallback_branch: Optional[str] = None

    try:
        if req.session_id:
            session = ensure_session(
                session_id=req.session_id,
                seller_id=req.seller_id,
                seller_name=req.seller_name,
            )
        else:
            session = create_session(
                seller_id=req.seller_id,
                seller_name=req.seller_name,
                title="Seller chat",
            )
        session_id = session.session_id

        if req.seller_name:
            upsert_memory_fact(session_id, "seller_name", req.seller_name)

        memory_facts_map = get_memory_facts(session_id)
        memory_facts = [f"{k}={v}" for k, v in memory_facts_map.items()]
        remembered_seller_name = memory_facts_map.get("seller_name")
        recent_turns = get_recent_turns(session_id=session_id, limit_pairs=3)

        initial_state_dict = _build_initial_state(
            req=req,
            session_id=session_id,
            memory_facts=memory_facts,
            recent_turns=recent_turns,
            remembered_seller_name=remembered_seller_name,
        )

        add_message(
            session_id=session_id,
            role="user",
            content=req.query,
            request_id=request_id,
        )

        final_state_dict = await _run_graph_with_trace(
            initial_state=initial_state_dict,
            session_id=session_id,
            request_id=request_id,
        )

        final_state = SellerState.model_validate(final_state_dict)

        if _should_apply_fallback(req.query, final_state):
            chosen = _pick_fallback_flag(req.query, final_state)
            if chosen and final_state.query is not None:
                fallback_applied = True
                fallback_branch = chosen
                rerun_state = final_state.model_copy(deep=True)
                rerun_state.query.fallback_override_flag = chosen
                rerun_state.answer_quality_signals["fallback_applied"] = 1.0

                rerun_state_dict = await _run_graph_with_trace(
                    initial_state=rerun_state.model_dump(),
                    session_id=session_id,
                    request_id=request_id,
                )
                final_state = SellerState.model_validate(rerun_state_dict)
                final_state.answer_quality_signals["fallback_applied"] = 1.0
                if final_state.query is not None:
                    final_state.query.fallback_override_flag = chosen

        if final_state.final_answer is None:
            logger.error(
                "Final state is missing final_answer",
                extra={"requested_mode": requested_mode_label},
            )
            raise HTTPException(
                status_code=500,
                detail="Copilot did not produce a final answer.",
            )

        final_mode_label = _mode_label_from_state(final_state)

        logger.info(
            "Analyze request completed",
            extra={
                "requested_mode": requested_mode_label,
                "final_mode": final_mode_label,
                "session_id": session_id,
                "request_id": request_id,
                "routing_confidence": (
                    final_state.query.routing_confidence
                    if final_state.query is not None
                    else None
                ),
                "active_branches": ",".join(final_state.active_branches),
                "skipped_branches": ",".join(final_state.skipped_branches),
                "fallback_applied": fallback_applied,
                "fallback_branch": fallback_branch,
            },
        )

        add_message(
            session_id=session_id,
            role="assistant",
            content=final_state.final_answer.answer_markdown,
            request_id=request_id,
            metadata={
                "used_tools": _extract_used_tools(final_state.execution_trace),
                "used_rag_evidence": _extract_rag_evidence(final_state),
                "rag_debug": _build_rag_debug(final_state),
                "routing_debug": _build_routing_debug(final_state),
                "execution_trace": final_state.execution_trace,
                "citations": (
                    final_state.final_answer.citations
                    if final_state.final_answer is not None
                    else []
                ),
                "session_id": session_id,
                "request_id": request_id,
                "fallback_applied": fallback_applied,
                "fallback_branch": fallback_branch,
            },
        )

        inferred_name = _extract_seller_name_from_text(req.query)
        if inferred_name:
            upsert_memory_fact(session_id, "seller_name", inferred_name)

        return AnalyzeResponse(
            final_answer=final_state.final_answer,
            critique=final_state.critique,
            hitl_feedback=final_state.hitl_feedback,
            execution_trace=final_state.execution_trace,
            used_tools=_extract_used_tools(final_state.execution_trace),
            used_rag_evidence=_extract_rag_evidence(final_state),
            rag_debug=_build_rag_debug(final_state),
            routing_debug=_build_routing_debug(final_state),
            session_id=session_id,
            request_id=request_id,
            state=final_state,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Unhandled error in analyze endpoint",
            extra={"error": str(exc)},
        )
        raise HTTPException(
            status_code=500,
            detail="Unexpected error while processing the request.",
        ) from exc
    finally:
        elapsed = time.perf_counter() - start_time
        copilot_request_latency_seconds.labels(mode=requested_mode_label).observe(
            elapsed
        )
