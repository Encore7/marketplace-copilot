from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

from ..schemas.rag import RAGChunk


@dataclass
class ChunkingConfig:
    """
    Configuration for heading-aware markdown chunking.
    """

    max_chars: int = 1200
    overlap_chars: int = 200
    respect_headings: bool = True


def _iter_markdown_sections(markdown: str) -> Iterable[tuple[str, str]]:
    """
    Yield (section_heading, section_body) pairs from markdown.

    This is a simple heading-aware splitter:
    - A section starts at a line beginning with '#' (any level).
    - Everything until the next heading belongs to that section.
    - If there is leading content before the first heading, we treat
      it as a section with heading "" (empty string).
    """
    lines = markdown.splitlines()
    current_heading: str = ""
    current_body: List[str] = []

    def flush_section() -> Optional[tuple[str, str]]:
        if not current_body and not current_heading:
            return None
        body_text = "\n".join(current_body).strip()
        if not body_text and not current_heading:
            return None
        return current_heading, body_text

    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("#"):
            # new section
            section = flush_section()
            if section is not None:
                yield section

            # Current line is heading
            current_heading = stripped.lstrip("#").strip()
            current_body = []
        else:
            current_body.append(line)

    section = flush_section()
    if section is not None:
        yield section


def _chunk_text(
    text: str,
    max_chars: int,
    overlap_chars: int,
) -> List[str]:
    """
    Chunk a block of text into overlapping windows of ~max_chars.

    This is a simple character-based splitter; in production you might
    want to swap in a token-based splitter. The interface is designed
    so that change is easy later.
    """
    text = text.strip()
    if not text:
        return []

    chunks: List[str] = []
    start = 0
    length = len(text)

    while start < length:
        end = min(start + max_chars, length)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == length:
            break
        # Move start with overlap
        start = max(0, end - overlap_chars)

    return chunks


def chunk_markdown_document(
    marketplace: str,
    section_name: str,
    source: Path,
    markdown: str,
    config: ChunkingConfig,
) -> List[RAGChunk]:
    """
    Chunk a single markdown document into RAGChunk instances.

    - Respects headings if configured
    - Applies size + overlap rules
    - Adds marketplace, section, source metadata
    """
    chunks: List[RAGChunk] = []
    base_id_prefix = f"{marketplace}:{section_name}:{source.name}"

    if config.respect_headings:
        sections = list(_iter_markdown_sections(markdown))
    else:
        sections = [("", markdown)]

    chunk_index = 0
    for heading, body in sections:
        if not body.strip():
            continue

        raw_chunks = _chunk_text(
            text=body,
            max_chars=config.max_chars,
            overlap_chars=config.overlap_chars,
        )
        for local_idx, chunk_text in enumerate(raw_chunks):
            chunk_id = f"{base_id_prefix}:{chunk_index}"
            logical_section = heading or section_name

            chunks.append(
                RAGChunk(
                    id=chunk_id,
                    text=chunk_text,
                    marketplace=marketplace,
                    section=logical_section,
                    source=str(source),
                )
            )
            chunk_index += 1

    return chunks
