from __future__ import annotations

import asyncio
import math
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from opensearchpy import OpenSearch
from sentence_transformers import SentenceTransformer

from ..core.config import settings
from ..observability.logging import get_logger
from ..schemas.rag import RAGChunk

logger = get_logger("rag.store")


class RAGStoreError(Exception):
    """Base exception for RAG store errors."""


@lru_cache(maxsize=1)
def _load_local_chunks() -> List[RAGChunk]:
    chunks_path = Path("data/rag/index/chunks.jsonl")
    if not chunks_path.exists():
        raise RAGStoreError(
            f"Local RAG chunks file not found: {chunks_path}. Run index builder first."
        )

    chunks: List[RAGChunk] = []
    with chunks_path.open("r", encoding="utf-8") as f:
        for line in f:
            text = line.strip()
            if not text:
                continue
            chunks.append(RAGChunk.model_validate_json(text))
    return chunks


def _score_text_overlap(query: str, text: str) -> float:
    query_terms = {t for t in query.lower().split() if t}
    if not query_terms:
        return 0.0

    text_terms = {t for t in text.lower().split() if t}
    overlap = len(query_terms.intersection(text_terms))
    denom = math.sqrt(len(query_terms) * max(1, len(text_terms)))
    return overlap / denom if denom > 0 else 0.0


def _retrieve_local_chunks(
    query: str,
    marketplace: Optional[str],
    section: Optional[str],
    top_k: int,
) -> List[RAGChunk]:
    chunks = _load_local_chunks()

    filtered = []
    for chunk in chunks:
        if marketplace and chunk.marketplace != marketplace:
            continue
        if section and chunk.section != section:
            continue
        filtered.append(chunk)

    scored = sorted(
        filtered,
        key=lambda c: _score_text_overlap(query=query, text=c.text),
        reverse=True,
    )
    out: List[RAGChunk] = []
    for chunk in scored[:top_k]:
        out.append(
            RAGChunk(
                id=chunk.id,
                text=chunk.text,
                marketplace=chunk.marketplace,
                section=chunk.section,
                source=chunk.source,
                score=_score_text_overlap(query=query, text=chunk.text),
            )
        )
    return out


def _new_opensearch_client() -> OpenSearch:
    return OpenSearch(
        hosts=[settings.rag.opensearch_url],
        timeout=settings.rag.opensearch_timeout_seconds,
        use_ssl=False,
        verify_certs=False,
    )


@lru_cache(maxsize=1)
def _get_embedder() -> SentenceTransformer:
    return SentenceTransformer(settings.llm.embed_model)


def _retrieve_opensearch_chunks(
    query: str,
    marketplace: Optional[str],
    section: Optional[str],
    top_k: int,
) -> List[RAGChunk]:
    filters: List[Dict[str, Any]] = []
    if marketplace:
        filters.append({"term": {"marketplace.keyword": marketplace}})
    if section:
        filters.append({"term": {"section.keyword": section}})

    should_clauses: List[Dict[str, Any]] = []
    try:
        query_vector = _get_embedder().encode(query).tolist()
        should_clauses.append(
            {
                "knn": {
                    "embedding": {
                        "vector": query_vector,
                        "k": top_k,
                    }
                }
            }
        )
    except Exception as exc:
        logger.warning(
            "Embedding generation failed; using lexical retrieval only",
            extra={"error": str(exc)},
        )

    payload: Dict[str, Any] = {
        "size": top_k,
        "_source": ["id", "text", "marketplace", "section", "source"],
        "query": {
            "bool": {
                "must": [
                    {
                        "multi_match": {
                            "query": query,
                            "fields": ["text^3", "source", "section"],
                        }
                    }
                ],
                "filter": filters,
                "should": should_clauses,
            }
        },
    }

    try:
        client = _new_opensearch_client()
        response = client.search(index=settings.rag.opensearch_index, body=payload)
    except Exception as exc:
        raise RAGStoreError(f"OpenSearch query failed: {exc}") from exc

    hits = response.get("hits", {}).get("hits", [])
    out: List[RAGChunk] = []
    for hit in hits:
        source = hit.get("_source", {})
        out.append(
            RAGChunk(
                id=source.get("id") or hit.get("_id") or "",
                text=source.get("text", ""),
                marketplace=source.get("marketplace"),
                section=source.get("section"),
                source=source.get("source"),
                score=hit.get("_score"),
            )
        )
    return out


async def async_retrieve_chunks(
    query: str,
    marketplace: Optional[str] = None,
    section: Optional[str] = None,
    top_k: Optional[int] = None,
    mode: Optional[str] = None,
) -> List[RAGChunk]:
    from pathlib import Path

    from .index_builder import load_rag_config

    rag_config = load_rag_config(Path("config/rag.yaml"))
    final_top_k = top_k or rag_config.retrieval.default_top_k
    final_top_k = min(final_top_k, rag_config.retrieval.max_top_k)

    final_mode = mode or rag_config.retrieval.mode
    if final_mode not in rag_config.retrieval.allowed_modes:
        raise RAGStoreError(f"Unsupported retrieval mode: {final_mode}")

    backend = settings.rag.backend
    logger.info(
        "RAG retrieval",
        extra={
            "backend": backend,
            "mode": final_mode,
            "top_k": final_top_k,
            "marketplace": marketplace or "any",
        },
    )

    if backend == "local_file":
        return await asyncio.to_thread(
            _retrieve_local_chunks,
            query,
            marketplace,
            section,
            final_top_k,
        )

    try:
        return await asyncio.to_thread(
            _retrieve_opensearch_chunks,
            query,
            marketplace,
            section,
            final_top_k,
        )
    except RAGStoreError as exc:
        logger.error(
            "OpenSearch backend failed, falling back to local_file",
            extra={"error": str(exc)},
        )
        return await asyncio.to_thread(
            _retrieve_local_chunks,
            query,
            marketplace,
            section,
            final_top_k,
        )
