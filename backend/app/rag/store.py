from __future__ import annotations

import asyncio
import math
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

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
    try:
        return SentenceTransformer(
            settings.llm.embed_model,
            local_files_only=True,
        )
    except Exception as exc:
        raise RAGStoreError(
            "Embedding model is not available in local cache. "
            "Preload it once with: "
            f"python -c \"from sentence_transformers import SentenceTransformer; "
            f"SentenceTransformer('{settings.llm.embed_model}')\""
        ) from exc


def _retrieve_opensearch_chunks(
    query: str,
    marketplace: Optional[str],
    section: Optional[str],
    top_k: int,
    mode: str,
) -> List[RAGChunk]:
    filters: List[Dict[str, Any]] = []
    if marketplace:
        filters.append({"term": {"marketplace": marketplace}})
    if section:
        filters.append({"term": {"section": section}})

    def _apply_python_filters(hits: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for hit in hits:
            src = hit.get("_source", {})
            if marketplace and src.get("marketplace") != marketplace:
                continue
            if section and src.get("section") != section:
                continue
            out.append(hit)
        return out

    def _search_lexical(client: OpenSearch, k: int) -> List[Dict[str, Any]]:
        payload: Dict[str, Any] = {
            "size": max(k, top_k),
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
                }
            },
        }
        response = client.search(index=settings.rag.opensearch_index, body=payload)
        return response.get("hits", {}).get("hits", [])

    def _search_vector(client: OpenSearch, k: int) -> List[Dict[str, Any]]:
        try:
            query_vector = _get_embedder().encode(query).tolist()
        except Exception as exc:
            raise RAGStoreError(
                f"Embedding generation failed for hybrid retrieval: {exc}"
            ) from exc

        # OpenSearch k-NN query; we apply metadata filters in Python for broad compatibility.
        payload: Dict[str, Any] = {
            "size": max(k, top_k),
            "_source": ["id", "text", "marketplace", "section", "source"],
            "query": {
                "knn": {
                    "embedding": {
                        "vector": query_vector,
                        "k": max(k, top_k),
                    }
                }
            },
        }
        response = client.search(index=settings.rag.opensearch_index, body=payload)
        hits = response.get("hits", {}).get("hits", [])
        return _apply_python_filters(hits)

    def _to_chunk(hit: Dict[str, Any], fused_score: float | None = None) -> RAGChunk:
        source = hit.get("_source", {})
        return RAGChunk(
            id=source.get("id") or hit.get("_id") or "",
            text=source.get("text", ""),
            marketplace=source.get("marketplace"),
            section=source.get("section"),
            source=source.get("source"),
            score=fused_score if fused_score is not None else hit.get("_score"),
        )

    def _rrf_fuse(
        lexical_hits: Sequence[Dict[str, Any]],
        vector_hits: Sequence[Dict[str, Any]],
        k_rrf: int = 60,
    ) -> List[Dict[str, Any]]:
        by_id: Dict[str, Dict[str, Any]] = {}
        fused: Dict[str, float] = {}

        for rank, hit in enumerate(lexical_hits, start=1):
            hid = hit.get("_id")
            if not hid:
                continue
            by_id[hid] = hit
            fused[hid] = fused.get(hid, 0.0) + (1.0 / (k_rrf + rank))

        for rank, hit in enumerate(vector_hits, start=1):
            hid = hit.get("_id")
            if not hid:
                continue
            by_id[hid] = hit
            fused[hid] = fused.get(hid, 0.0) + (1.0 / (k_rrf + rank))

        ranked_ids = sorted(fused.keys(), key=lambda hid: fused[hid], reverse=True)
        out: List[Dict[str, Any]] = []
        for hid in ranked_ids:
            h = by_id[hid].copy()
            h["_rrf_score"] = fused[hid]
            out.append(h)
        return out

    try:
        client = _new_opensearch_client()
        if mode == "bm25":
            hits = _search_lexical(client, k=top_k)
            return [_to_chunk(hit) for hit in hits[:top_k]]
        if mode == "vector":
            hits = _search_vector(client, k=top_k)
            return [_to_chunk(hit) for hit in hits[:top_k]]

        # hybrid -> lexical + vector fused with Reciprocal Rank Fusion (RRF)
        lexical_hits = _search_lexical(client, k=max(top_k * 3, 20))
        vector_hits = _search_vector(client, k=max(top_k * 3, 20))
        fused_hits = _rrf_fuse(lexical_hits, vector_hits)
        return [_to_chunk(hit, fused_score=hit.get("_rrf_score")) for hit in fused_hits[:top_k]]
    except Exception as exc:
        raise RAGStoreError(f"OpenSearch query failed: {exc}") from exc


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

    return await asyncio.to_thread(
        _retrieve_opensearch_chunks,
        query,
        marketplace,
        section,
        final_top_k,
        final_mode,
    )
