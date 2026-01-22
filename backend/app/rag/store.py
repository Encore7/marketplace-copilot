from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx

from ..core.config import settings
from ..observability.logging import get_logger
from ..schemas.rag import RAGChunk

logger = get_logger("rag.store")


class RAGStoreError(Exception):
    """Base exception for RAG store errors."""


async def async_retrieve_chunks(
    query: str,
    marketplace: Optional[str] = None,
    section: Optional[str] = None,
    top_k: Optional[int] = None,
    mode: Optional[str] = None,
) -> List[RAGChunk]:
    """
    Query the external vector store for relevant RAG chunks.

    This function is async so it can be used from async endpoints or agents.
    A sync wrapper can be added later if needed.

    - query: natural language query
    - marketplace: optional filter (amazon, flipkart, ...)
    - section: optional filter (image_requirements, listing_guidelines, ...)
    - top_k: override default_top_k from RAG config, capped at max_top_k
    - mode: retrieval mode: "hybrid" | "vector" | "bm25"
    """
    from pathlib import Path

    from .index_builder import load_rag_config

    # Load retrieval config
    rag_config = load_rag_config(Path("config/rag.yaml"))

    final_top_k = top_k or rag_config.retrieval.default_top_k
    final_top_k = min(final_top_k, rag_config.retrieval.max_top_k)

    final_mode = mode or rag_config.retrieval.mode
    if final_mode not in rag_config.retrieval.allowed_modes:
        raise RAGStoreError(f"Unsupported retrieval mode: {final_mode}")

    filters: Dict[str, Any] = {}
    if marketplace:
        filters["marketplace"] = marketplace
    if section:
        filters["section"] = section

    payload: Dict[str, Any] = {
        "collection": settings.rag.vector_store_collection,
        "query": query,
        "top_k": final_top_k,
        "mode": final_mode,
        "filters": filters,
    }

    logger.info(
        "RAG query",
        extra={
            "mode": final_mode,
            "marketplace": marketplace or "any",
            "top_k": final_top_k,
        },
    )

    async with httpx.AsyncClient(
        base_url=settings.rag.vector_store_url,
        timeout=10.0,
    ) as client:
        try:
            response = await client.post("/query", json=payload)
        except httpx.RequestError as exc:
            logger.error(
                "Error querying RAG vector store",
                extra={"error": str(exc)},
            )
            raise RAGStoreError("Failed to reach RAG vector store") from exc

    if response.status_code != 200:
        logger.error(
            "RAG vector store returned non-200 status",
            extra={
                "status_code": response.status_code,
                "body": response.text[:500],
            },
        )
        raise RAGStoreError(f"RAG vector store error: {response.status_code}")

    data = response.json()
    raw_results = data.get("results", [])

    chunks: List[RAGChunk] = []
    for item in raw_results:
        try:
            chunks.append(RAGChunk.model_validate(item))
        except Exception as exc:
            logger.error(
                "Failed to validate RAG result item",
                extra={"error": str(exc)},
            )
            continue

    return chunks
