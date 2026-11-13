"""Structure-aware chunker.

Public API: chunk_document(parsed_doc, target_size=500, max_size=800)

Strategy:
  1. If a section fits in target_size, it becomes one chunk.
  2. If a section exceeds max_size, split it into paragraph-aligned
     sub-chunks. Each sub-chunk preserves the parent section heading.
  3. If even a single paragraph exceeds max_size, fall back to
     sliding-window chunking on that paragraph (W6's approach).

This is the W8 upgrade vs W6's pure sliding window:
  - Boundaries respect document structure
  - Each chunk knows its parent section + heading
  - Cross-section bleed is eliminated
  - Heading text is included in the chunk for retrieval signal
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from src.ingest.parsers import ParsedDocument, ParsedSection


@dataclass
class Chunk:
    """W8 chunk — extended from W6's (text, source) with rich metadata.

    The metadata dict is what makes Qdrant filtering possible. NOTE: the
    `source` field is also stored in metadata so it lands in the Qdrant
    payload — keeping it only on the dataclass means downstream code
    that builds payloads from metadata alone misses it.
    """
    text: str
    source: str
    metadata: dict = field(default_factory=dict)


# ─── Chunking strategy: structure-aware with sliding-window fallback ────

def chunk_document(
    parsed_doc: ParsedDocument,
    target_size: int = 500,
    max_size: int = 800,
    overlap: int = 50,
) -> list[Chunk]:
    """Produce structure-aware chunks from a parsed document.

    Args:
        parsed_doc: output of parse_document(...)
        target_size: ideal chunk size in characters
        max_size: hard ceiling — chunks larger than this get split
        overlap: characters of overlap between sliding-window splits

    Returns:
        List of Chunk objects with metadata.
    """
    chunks: list[Chunk] = []

    # If no sections were extracted (e.g. .txt or empty doc),
    # fall back to sliding window on the raw text.
    if not parsed_doc.sections:
        if not parsed_doc.raw_text.strip():
            return []
        return _sliding_window_chunks(
            text=parsed_doc.raw_text,
            source=parsed_doc.source,
            base_metadata={
                "source": parsed_doc.source,        # ← FIX: include source
                "doc_title": parsed_doc.doc_title,
                "doc_type": parsed_doc.doc_type,
                "section_path": "",
                "heading": "",
                "heading_level": 0,
                "page": None,
            },
            target_size=target_size,
            overlap=overlap,
        )

    # Walk sections, build section_path as we go
    section_path_stack: list[str] = []
    last_levels: list[int] = []

    for section in parsed_doc.sections:
        # Maintain a section_path that reflects the heading hierarchy
        section_path_stack = _update_section_path(
            section_path_stack, last_levels, section.heading, section.level,
        )
        last_levels = (
            last_levels[: len(section_path_stack) - 1] + [section.level]
        )
        section_path = " > ".join(section_path_stack)

        base_metadata = {
            "source": parsed_doc.source,            # ← FIX: include source
            "doc_title": parsed_doc.doc_title,
            "doc_type": parsed_doc.doc_type,
            "section_path": section_path,
            "heading": section.heading,
            "heading_level": section.level,
            "page": section.page,
        }

        # Decide how to chunk this section
        section_text = section.text.strip()
        if not section_text:
            continue

        # Prepend heading to chunk text — improves retrieval signal
        heading_prefix = f"## {section.heading}\n" if section.heading else ""
        full_text = heading_prefix + section_text

        if len(full_text) <= max_size:
            # Whole section fits — one chunk
            chunks.append(Chunk(
                text=full_text,
                source=parsed_doc.source,
                metadata={**base_metadata, "char_length": len(full_text)},
            ))
        else:
            # Section too big — split by paragraph first
            chunks.extend(_paragraph_split_chunks(
                text=section_text,
                heading=section.heading,
                source=parsed_doc.source,
                base_metadata=base_metadata,
                target_size=target_size,
                max_size=max_size,
                overlap=overlap,
            ))

    return chunks


# ─── Helpers ────────────────────────────────────────────────────────────

def _update_section_path(
    stack: list[str], last_levels: list[int],
    new_heading: str, new_level: int,
) -> list[str]:
    """Maintain the running section_path as we walk the heading
    hierarchy. Pops levels that the new heading replaces.
    """
    # Pop any deeper levels off the stack
    while last_levels and last_levels[-1] >= new_level:
        stack = stack[:-1]
        last_levels = last_levels[:-1]
    stack = stack + [new_heading]
    return stack


def _paragraph_split_chunks(
    text: str, heading: str, source: str, base_metadata: dict,
    target_size: int, max_size: int, overlap: int,
) -> list[Chunk]:
    """Split a too-large section by paragraph boundaries.

    Accumulates paragraphs until target_size is reached, then emits.
    If a single paragraph exceeds max_size, fall back to sliding-window.
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        # No paragraph breaks; fallback to sliding window
        return _sliding_window_chunks(
            text=text, source=source, base_metadata=base_metadata,
            target_size=target_size, overlap=overlap,
        )

    chunks: list[Chunk] = []
    heading_prefix = f"## {heading}\n" if heading else ""
    current_parts: list[str] = []
    current_size = len(heading_prefix)

    def emit():
        if current_parts:
            text = heading_prefix + "\n\n".join(current_parts)
            chunks.append(Chunk(
                text=text,
                source=source,
                metadata={**base_metadata, "char_length": len(text)},
            ))

    for para in paragraphs:
        para_size = len(para) + 2  # account for paragraph break

        if para_size > max_size:
            # Single paragraph is too large — flush current, then sliding-window
            emit()
            current_parts = []
            current_size = len(heading_prefix)
            chunks.extend(_sliding_window_chunks(
                text=para, source=source, base_metadata=base_metadata,
                target_size=target_size, overlap=overlap,
            ))
            continue

        if current_size + para_size > target_size and current_parts:
            emit()
            current_parts = [para]
            current_size = len(heading_prefix) + para_size
        else:
            current_parts.append(para)
            current_size += para_size

    emit()
    return chunks


def _sliding_window_chunks(
    text: str, source: str, base_metadata: dict,
    target_size: int, overlap: int,
) -> list[Chunk]:
    """W6's sliding window — used as last-resort fallback only."""
    chunks: list[Chunk] = []
    start = 0
    while start < len(text):
        end = start + target_size
        piece = text[start:end]
        if piece.strip():
            chunks.append(Chunk(
                text=piece,
                source=source,
                metadata={**base_metadata, "char_length": len(piece)},
            ))
        next_start = end - overlap
        if next_start <= start or end >= len(text):
            break
        start = next_start
    return chunks
