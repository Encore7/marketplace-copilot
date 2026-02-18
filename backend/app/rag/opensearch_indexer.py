from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict, List

from opensearchpy import OpenSearch, helpers
from sentence_transformers import SentenceTransformer

from ..core.config import settings
from ..observability.logging import get_logger

logger = get_logger("rag.opensearch_indexer")


def _new_client() -> OpenSearch:
    return OpenSearch(
        hosts=[settings.rag.opensearch_url],
        use_ssl=False,
        verify_certs=False,
    )


def _mapping(dims: int) -> Dict:
    return {
        "settings": {
            "index": {
                "number_of_shards": 1,
                "number_of_replicas": 0,
                "knn": True,
            }
        },
        "mappings": {
            "properties": {
                "id": {"type": "keyword"},
                "text": {"type": "text"},
                "marketplace": {"type": "keyword"},
                "section": {"type": "keyword"},
                "source": {"type": "keyword"},
                "embedding": {"type": "knn_vector", "dimension": dims},
            }
        },
    }


def seed_opensearch_index(chunks_path: Path | None = None) -> None:
    if chunks_path is None:
        chunks_path = Path("data/rag/index/chunks.jsonl")

    if not chunks_path.exists():
        raise FileNotFoundError(
            f"RAG chunks file not found: {chunks_path}. Run `index_builder` first."
        )

    client = _new_client()
    index = settings.rag.opensearch_index
    try:
        embedder = SentenceTransformer(
            settings.llm.embed_model,
            local_files_only=True,
        )
    except Exception as exc:
        raise RuntimeError(
            "Embedding model is not available in local cache. "
            "Preload it once with: "
            f"python -c \"from sentence_transformers import SentenceTransformer; "
            f"SentenceTransformer('{settings.llm.embed_model}')\""
        ) from exc
    dims = int(embedder.get_sentence_embedding_dimension())

    for _ in range(120):
        try:
            if client.ping():
                break
        except Exception:
            pass
        time.sleep(1)
    else:
        raise RuntimeError(
            f"OpenSearch is not reachable for indexing at {settings.rag.opensearch_url}"
        )

    if client.indices.exists(index=index):
        client.indices.delete(index=index)
    client.indices.create(index=index, body=_mapping(dims))

    actions: List[Dict] = []
    with chunks_path.open("r", encoding="utf-8") as f:
        for line in f:
            raw = line.strip()
            if not raw:
                continue
            chunk = json.loads(raw)
            source_doc = {
                "id": chunk.get("id"),
                "text": chunk.get("text", ""),
                "marketplace": chunk.get("marketplace"),
                "section": chunk.get("section"),
                "source": chunk.get("source"),
                "embedding": embedder.encode(chunk.get("text", "")).tolist(),
            }

            actions.append(
                {
                    "_index": index,
                    "_id": chunk["id"],
                    "_source": source_doc,
                }
            )

    if actions:
        helpers.bulk(client, actions, refresh=True)

    logger.info(
        "OpenSearch seed complete",
        extra={"index": index, "num_chunks": len(actions)},
    )


if __name__ == "__main__":
    seed_opensearch_index()
