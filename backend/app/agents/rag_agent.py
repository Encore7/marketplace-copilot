from __future__ import annotations

from typing import List, Optional

from ..core.config import settings
from ..observability.logging import get_logger
from ..schemas.rag import RAGChunk
from ..tools.rag_tool import RAGQueryInput, query_rag
from .state import RAGContext, SellerState

logger = get_logger("agents.rag")

_SUPPORTED_MARKETPLACES: List[str] = ["amazon", "flipkart", "meesho", "myntra"]


def _choose_primary_marketplace(marketplaces: List[str]) -> Optional[str]:
    """
    Pick a primary marketplace for RAG.

    Strategy:
      - If any requested marketplace is supported, pick the first supported.
      - Else, return None => cross-market / generic retrieval.
    """
    for m in marketplaces:
        if m in _SUPPORTED_MARKETPLACES:
            return m
    return None


async def update_rag_context(
    state: SellerState,
    top_k: int = 8,
    mode: str = "hybrid",
) -> SellerState:
    """
    RAG Agent.

    Responsibilities:
      - Use the user's query + marketplaces to retrieve relevant policy/SEO chunks
        from the external RAG store (pre-indexed offline).
      - Populate `state.rag_context` with structured RAG chunks.

    This is async because the underlying rag_tool is async.
    """
    if state.query is None:
        raise ValueError(
            "RagAgent: state.query is missing; initial state is malformed."
        )

    raw_query = state.query.raw_query or ""
    marketplaces = state.query.marketplaces or list(_SUPPORTED_MARKETPLACES)
    primary_marketplace = _choose_primary_marketplace(marketplaces)

    logger.info(
        "RAG agent querying index",
        extra={
            "query_snippet": raw_query[:80],
            "primary_marketplace": primary_marketplace or "any",
            "top_k": top_k,
            "mode": mode,
        },
    )

    # Build input for the tool
    input_data = RAGQueryInput(
        query=raw_query,
        marketplace=primary_marketplace,
        section=None,
        top_k=top_k,
        mode=mode,
    )

    # Call async tool
    out = await query_rag(input_data)

    chunks: List[RAGChunk] = out.chunks

    if not chunks:
        logger.info(
            "RAG agent: no chunks returned",
            extra={"primary_marketplace": primary_marketplace or "any"},
        )

    state.rag_context = RAGContext(
        query=raw_query,
        marketplace=primary_marketplace,
        section=None,
        backend=settings.rag.backend,
        retrieval_mode=mode,
        fusion_method="rrf" if mode == "hybrid" else None,
        chunks=chunks,
    )

    logger.info(
        "RAG agent updated rag_context",
        extra={
            "primary_marketplace": primary_marketplace or "any",
            "num_chunks": len(chunks),
        },
    )

    return state
