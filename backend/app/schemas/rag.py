from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field
from pydantic.config import ConfigDict


class RAGChunk(BaseModel):
    """
    A single retrieved chunk from the RAG vector store.

    This is intentionally model-agnostic: the vector store service is
    responsible for chunking and indexing. We only consume metadata.
    """

    model_config = ConfigDict(extra="ignore")

    id: str = Field(..., description="Chunk identifier in the vector store.")
    text: str = Field(..., description="Raw text of the chunk.")
    marketplace: Optional[str] = Field(
        default=None,
        description="Marketplace this policy/guideline chunk belongs to.",
    )
    section: Optional[str] = Field(
        default=None,
        description="Logical section, e.g. 'image_requirements', 'seo_best_practices'.",
    )
    source: Optional[str] = Field(
        default=None,
        description="Document/source identifier inside the RAG corpus.",
    )
    score: Optional[float] = Field(
        default=None,
        description="Relevance score from the retriever (higher = more relevant).",
    )
