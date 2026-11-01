"""Chunker — sliding-window chunker, carried forward from W6.

W7 deliberately does NOT change chunking. Chunking strategies are
W8's territory (Document Ingestion + PII Awareness).

This is the same chunker the cohort built in W6's live coding session.
We retain it so that any KPI delta in W7 can be attributed to the
embedding model or vector store change, NOT to a different chunker.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class Chunk:
    """A piece of text with its source document name.

    W6's Chunk has just (text, source). W8 will extend it with metadata.
    For W7 we keep it identical to W6.
    """
    text: str
    source: str


def chunk_text(text: str, source: str, size: int = 500, overlap: int = 50) -> list[Chunk]:
    """Sliding-window chunker. Cuts mid-sentence on purpose.

    This is the W6 chunker — naive, by design. Learners SAW the problem
    in W6 (chunks cut mid-sentence; answers lose context). The fix is
    section-aware chunking in W8.
    """
    chunks: list[Chunk] = []
    start = 0
    while start < len(text):
        end = start + size
        piece = text[start:end]
        if piece.strip():
            chunks.append(Chunk(text=piece, source=source))
        start = end - overlap
        if start <= 0 or end >= len(text):
            break
    return chunks


def chunk_corpus(corpus_dir: str = "data/corpus", size: int = 500,
                 overlap: int = 50) -> list[Chunk]:
    """Chunk every .md document in a directory."""
    path = Path(corpus_dir)
    if not path.exists():
        raise FileNotFoundError(f"Corpus directory not found: {corpus_dir}")

    all_chunks: list[Chunk] = []
    for doc_path in sorted(path.glob("*.md")):
        raw = doc_path.read_text(encoding="utf-8")
        all_chunks.extend(chunk_text(raw, source=doc_path.name,
                                       size=size, overlap=overlap))
    return all_chunks
