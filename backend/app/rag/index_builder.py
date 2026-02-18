from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import yaml

from ..schemas.rag import RAGChunk
from .chunker import ChunkingConfig, chunk_markdown_document


@dataclass
class RAGRetrievalConfig:
    default_top_k: int
    max_top_k: int
    mode: str
    allowed_modes: List[str]


@dataclass
class RAGConfig:
    markdown_root: Path
    index_output_dir: Path
    marketplaces: List[str]
    chunking: ChunkingConfig
    retrieval: RAGRetrievalConfig


def load_rag_config(config_path: Path) -> RAGConfig:
    """
    Load RAG configuration from a YAML file.
    """
    with config_path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    rag_cfg: Dict = raw["rag"]

    markdown_root = Path(rag_cfg["markdown_root"])
    index_output_dir = Path(rag_cfg["index_output_dir"])

    chunk_cfg_raw = rag_cfg["chunking"]
    chunk_cfg = ChunkingConfig(
        max_chars=int(chunk_cfg_raw.get("max_chars", 1200)),
        overlap_chars=int(chunk_cfg_raw.get("overlap_chars", 200)),
        respect_headings=bool(chunk_cfg_raw.get("respect_headings", True)),
    )

    retrieval_raw = rag_cfg["retrieval"]
    retrieval_cfg = RAGRetrievalConfig(
        default_top_k=int(retrieval_raw.get("default_top_k", 8)),
        max_top_k=int(retrieval_raw.get("max_top_k", 32)),
        mode=str(retrieval_raw.get("mode", "hybrid")),
        allowed_modes=list(
            retrieval_raw.get("allowed_modes", ["hybrid", "vector", "bm25"])
        ),
    )

    marketplaces = list(rag_cfg.get("marketplaces", []))

    return RAGConfig(
        markdown_root=markdown_root,
        index_output_dir=index_output_dir,
        marketplaces=marketplaces,
        chunking=chunk_cfg,
        retrieval=retrieval_cfg,
    )


def _discover_markdown_files(
    root: Path, marketplaces: List[str]
) -> List[tuple[str, Path, str]]:
    """
    Discover markdown files under markdown_root.

    Returns a list of (marketplace, path, section_name) tuples.
    The current layout expected is:

        root/
          amazon/
            image_requirements.md
            listing_guidelines.md
            ...

    section_name is derived from the filename without extension.
    """
    discovered: List[tuple[str, Path, str]] = []

    for marketplace in marketplaces:
        marketplace_dir = root / marketplace
        if not marketplace_dir.exists():
            continue

        for path in marketplace_dir.glob("*.md"):
            section_name = path.stem  # e.g. "image_requirements"
            discovered.append((marketplace, path, section_name))

    return discovered


def build_rag_index(config_path: Path | None = None) -> None:
    """
    Offline RAG index builder.

    - Loads config/rag.yaml
    - Reads markdown docs
    - Chunks them into RAGChunk objects
    - Writes them to data/rag/index/chunks.jsonl as an intermediate artifact
    - Optionally, this is where you'd push chunks into your external vector store

    This function is NOT used at request time.
    """
    if config_path is None:
        config_path = Path("config/rag.yaml")

    rag_config = load_rag_config(config_path)

    rag_config.index_output_dir.mkdir(parents=True, exist_ok=True)
    chunks_path = rag_config.index_output_dir / "chunks.jsonl"

    discovered = _discover_markdown_files(
        root=rag_config.markdown_root,
        marketplaces=rag_config.marketplaces,
    )

    all_chunks: List[RAGChunk] = []

    for marketplace, path, section_name in discovered:
        markdown = path.read_text(encoding="utf-8")
        doc_chunks = chunk_markdown_document(
            marketplace=marketplace,
            section_name=section_name,
            source=path,
            markdown=markdown,
            config=rag_config.chunking,
        )
        all_chunks.extend(doc_chunks)

    # Write intermediate artifact
    with chunks_path.open("w", encoding="utf-8") as f:
        for chunk in all_chunks:
            f.write(chunk.model_dump_json() + "\n")


if __name__ == "__main__":
    build_rag_index()
