from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

from ..observability.logging import get_logger
from ..rag.store import RAGStoreError, async_retrieve_chunks
from ..schemas.rag import RAGChunk

logger = get_logger("tools.rag")


class RAGQueryInput(BaseModel):
    """
    Input for RAG retrieval tool.

    RAG is only used for:
      - Policies
      - SEO guidelines
      - Listing rules
      - Restricted words
      - Image rules
    """

    query: str = Field(
        ..., description="Natural language query about marketplace rules"
    )
    marketplace: Optional[str] = Field(
        default=None,
        description="Marketplace filter (amazon, flipkart, meesho, myntra)",
    )
    section: Optional[str] = Field(
        default=None,
        description="Optional section filter (e.g. 'image_requirements')",
    )
    top_k: Optional[int] = Field(
        default=None,
        description="Override default_top_k if needed (capped by max_top_k).",
    )
    mode: Optional[str] = Field(
        default=None,
        description='Retrieval mode: "hybrid" | "vector" | "bm25".',
    )


class RAGQueryOutput(BaseModel):
    """
    Output of the RAG retrieval tool: the retrieved chunks.
    """

    chunks: List[RAGChunk]


async def query_rag(input_data: RAGQueryInput) -> RAGQueryOutput:
    """
    Tool: Query the external RAG store and return structured chunks.

    Agents will typically:
      - call this tool
      - feed chunks into LLM prompts for answer synthesis
      - use citations (source/section) to show where claims come from
    """
    logger.info(
        "RAG tool query",
        extra={
            "marketplace": input_data.marketplace or "any",
            "section": input_data.section or "any",
            "mode": input_data.mode or "default",
        },
    )

    try:
        chunks = await async_retrieve_chunks(
            query=input_data.query,
            marketplace=input_data.marketplace,
            section=input_data.section,
            top_k=input_data.top_k,
            mode=input_data.mode,
        )
    except RAGStoreError as exc:
        logger.error(
            "RAG store error in rag_tool",
            extra={"error": str(exc)},
        )
        raise

    return RAGQueryOutput(chunks=chunks)
