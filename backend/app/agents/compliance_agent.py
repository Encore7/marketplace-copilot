from __future__ import annotations

from typing import Dict, List, Optional

from ..observability.logging import get_logger
from ..tools.rag_tool import RAGQueryInput, query_rag
from .state import ComplianceAnalysis, RAGContext, SellerState

logger = get_logger("agents.compliance")


def _pick_primary_marketplace(state: SellerState) -> Optional[str]:
    """
    Choose a primary marketplace for RAG filtering.

    Priority:
      1) state.query.marketplaces[0], if provided
      2) seller_profile.marketplaces[0]
      3) None (means 'any' in RAG)
    """
    if state.query and state.query.marketplaces:
        return state.query.marketplaces[0]
    if state.seller_profile and state.seller_profile.marketplaces:
        return state.seller_profile.marketplaces[0]
    return None


def _compliance_rag_query(state: SellerState) -> str:
    """
    Build a canonical RAG query for compliance/policy retrieval.

    We don't just send raw user query; we wrap it with a consistent intent
    so the RAG store retrieves the right kind of docs.
    """
    base = (
        "You are retrieving marketplace policy and listing rules relevant to this seller. "
        "Focus on listing guidelines, image requirements, restricted products, and SEO rules."
    )
    if state.query is None:
        return base

    return base + " The user query is: " + state.query.raw_query


async def update_compliance_and_rag(state: SellerState) -> SellerState:
    """
    Compliance Agent (phase 1).

    Responsibilities (for now):
      - Retrieve relevant policy/guideline chunks via RAG
      - Populate SellerState.rag_context with those chunks
      - Create placeholder ComplianceAnalysis entries per product (no issues yet)

    Later, this agent will:
      - use an LLM to interpret listing content against these policies
      - populate structured ComplianceIssue objects with severities + citations
    """
    # Decide primary marketplace to scope RAG
    marketplace = _pick_primary_marketplace(state)
    rag_query_text = _compliance_rag_query(state)

    rag_input = RAGQueryInput(
        query=rag_query_text,
        marketplace=marketplace,
        section=None,
        top_k=20,
        mode="hybrid",
    )

    try:
        rag_output = await query_rag(rag_input)
    except Exception as exc:
        logger.error(
            "Compliance agent: RAG query failed",
            extra={"error": str(exc)},
        )
        # We leave state.rag_context and compliance_analyses unchanged on failure
        return state

    # Attach global RAG context
    state.rag_context = RAGContext(
        query=rag_query_text,
        marketplace=marketplace,
        section=None,
        chunks=rag_output.chunks,
    )

    product_ids: List[str] = []
    if state.product_selection and state.product_selection.selected_product_ids:
        product_ids = state.product_selection.selected_product_ids

    existing_by_product: Dict[Optional[str], ComplianceAnalysis] = {
        a.product_id: a for a in state.compliance_analyses
    }
    updated_by_product: Dict[Optional[str], ComplianceAnalysis] = {}

    # If no explicit products, we still produce a global compliance analysis
    if not product_ids:
        product_ids = [None]

    for pid in product_ids:
        summary_parts: List[str] = []

        summary_parts.append(
            "Compliance analysis is in an initial phase: "
            "policy and guideline chunks have been retrieved via RAG, "
            "but detailed, per-listing rule checks are not yet implemented."
        )
        if marketplace:
            summary_parts.append(
                f" Policies are scoped primarily to marketplace: {marketplace}."
            )
        else:
            summary_parts.append(" Policies are not scoped to a single marketplace.")

        summary_parts.append(
            " Downstream LLM-based compliance checks will use these chunks "
            "to flag potential issues and attach precise citations."
        )

        summary_text = " ".join(summary_parts)

        analysis = existing_by_product.get(pid) or ComplianceAnalysis(
            product_id=pid,
            issues=[],
            summary=summary_text,
        )

        # For now we don't add issues; that will come when we add LLM reasoning
        updated_by_product[pid] = analysis

    state.compliance_analyses = list(updated_by_product.values())

    logger.info(
        "Compliance agent updated RAG context and compliance analyses",
        extra={
            "num_chunks": len(rag_output.chunks),
            "num_analyses": len(state.compliance_analyses),
        },
    )

    return state
