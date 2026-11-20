"""Metadata schema for W8 chunks.

This module defines the 7 metadata fields every chunk gets, and helpers
for extracting / validating them.

Why this exists as its own module: the curriculum's W3 lesson taught
"data contracts via Pydantic". W8 reinforces that lesson — the chunk
payload is a small data contract, not arbitrary dict.

The fields:
  source           — filename (e.g. "leave_policy.pdf")
  doc_title        — extracted human title (e.g. "Leave Policy")
  doc_type         — "hr" / "it" / "general" (taxonomy)
  section_path     — heading hierarchy (e.g. "Leave > Annual Leave")
  page             — page number for PDFs; None otherwise
  ingested_at      — ISO 8601 timestamp of ingestion
  has_pii          — True if any PII was scrubbed
  pii_types        — list of PII types found (for audit)
  char_length      — chunk text length (for debugging)
"""
from __future__ import annotations

from datetime import datetime, timezone


# The canonical list of fields. Used by validators.
METADATA_FIELDS = (
    "source",
    "doc_title",
    "doc_type",
    "section_path",
    "page",
    "ingested_at",
    "has_pii",
    "pii_types",
    "char_length",
)


def make_ingestion_timestamp() -> str:
    """Return an ISO 8601 UTC timestamp for the ingested_at field."""
    return datetime.now(timezone.utc).isoformat()


def finalize_metadata(chunks: list, ingested_at: str | None = None) -> list:
    """Ensure every chunk has the complete metadata schema.

    Pipeline ordering:
      1. parse_document → ParsedDocument
      2. chunk_document → chunks with most metadata fields
      3. scrub_chunks → adds has_pii + pii_types
      4. finalize_metadata → adds ingested_at + fills missing keys

    Args:
        chunks: list of Chunk objects.
        ingested_at: optional override; defaults to now().

    Returns:
        The same list, with metadata dicts complete.
    """
    ts = ingested_at or make_ingestion_timestamp()

    for chunk in chunks:
        meta = chunk.metadata if isinstance(chunk.metadata, dict) else {}
        meta.setdefault("ingested_at", ts)
        meta.setdefault("has_pii", False)
        meta.setdefault("pii_types", [])
        meta.setdefault("char_length", len(chunk.text))
        # Ensure all canonical fields exist (None if absent)
        for field in METADATA_FIELDS:
            meta.setdefault(field, None)
        chunk.metadata = meta
    return chunks


def validate_metadata(chunk) -> list[str]:
    """Return a list of validation errors (empty if valid).

    Used in audit / debugging.
    """
    errors: list[str] = []
    if not isinstance(chunk.metadata, dict):
        return ["metadata is not a dict"]
    required = ("source", "doc_title", "doc_type")
    for field in required:
        if not chunk.metadata.get(field):
            errors.append(f"missing required field: {field}")
    if chunk.metadata.get("has_pii") and not chunk.metadata.get("pii_types"):
        errors.append("has_pii=True but pii_types is empty")
    return errors


def summarize_metadata(chunks: list) -> dict:
    """Return a quick summary of metadata coverage across chunks.

    Useful for QA: how many chunks have PII? How many doc_types? etc.
    """
    if not chunks:
        return {"n_chunks": 0}
    n = len(chunks)
    has_pii = sum(1 for c in chunks if c.metadata.get("has_pii"))
    doc_types: dict[str, int] = {}
    sources: dict[str, int] = {}
    for c in chunks:
        dt = c.metadata.get("doc_type") or "unknown"
        doc_types[dt] = doc_types.get(dt, 0) + 1
        src = c.metadata.get("source") or "unknown"
        sources[src] = sources.get(src, 0) + 1
    return {
        "n_chunks": n,
        "chunks_with_pii": has_pii,
        "pii_ratio": round(has_pii / n, 3),
        "doc_types": doc_types,
        "n_sources": len(sources),
        "sources": sorted(sources.keys()),
    }
