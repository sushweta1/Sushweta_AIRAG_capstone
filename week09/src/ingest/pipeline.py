"""End-to-end ingestion pipeline.

This is the W8 centerpiece — what gets built during the 50-min live
coding block. About 130 lines orchestrating the four W8 modules:

  1. parsers.parse_document  → format-aware extraction
  2. chunkers.chunk_document → structure-aware chunking
  3. pii.scrub_chunks        → regex + Presidio PII removal
  4. metadata.finalize_metadata → schema completion

Then upsert to Qdrant with the new metadata-rich payload, AND create
payload indexes so filtering works at query time.

Public API:

    ingest_corpus(corpus_dir, embedding_model, collection_name, use_presidio)
        → IngestionResult

The IngestionResult is the audit trail — what was ingested, what was
skipped, how much PII was found, etc.
"""
from __future__ import annotations

# Bootstrap before any heavy imports
from src import _bootstrap  # noqa: F401

import uuid
from dataclasses import dataclass, field
from pathlib import Path

from src.ingest.parsers import parse_document, detect_format
from src.ingest.chunkers import Chunk, chunk_document
from src.ingest.pii import scrub_chunks
from src.ingest.metadata import (
    finalize_metadata,
    make_ingestion_timestamp,
    summarize_metadata,
)
from src.rag.embeddings import EMBEDDING_DIMS, embed


COLLECTION_NAME_V2 = "capstone_chunks_v2"
SUPPORTED_EXTENSIONS = (".pdf", ".html", ".htm", ".docx", ".md", ".txt")


# ─── Payload indexes ────────────────────────────────────────────────────
# Qdrant Cloud requires a payload index on any field used in a filter.
# Storage of payload fields is free; filtering on them requires opting
# in per-field. We index every field the W8 / W9 curriculum filters on.
#
# Field schemas:
#   KEYWORD  — string fields used in equality filtering (MatchValue)
#   INTEGER  — numeric fields for range / equality
#   BOOL     — true/false flags
#   TEXT     — full-text search (we don't use this — equality is enough)
#
# This list is the single source of truth. If you add a field to the
# metadata schema and want to filter on it, add it here too.

PAYLOAD_INDEX_FIELDS = [
    ("doc_type",      "keyword"),  # 'hr' / 'it' / 'general'
    ("has_pii",       "bool"),     # True if PII was scrubbed
    ("source",        "keyword"),  # filename
    ("doc_title",     "keyword"),  # extracted document title
    ("section_path",  "keyword"),  # 'Leave Policy > Annual Leave'
    ("heading",       "keyword"),  # nearest heading text
    ("heading_level", "integer"),  # 1, 2, 3, …
    ("page",          "integer"),  # PDF page number; absent for non-paginated
]


@dataclass
class IngestionResult:
    """Audit trail of one ingest_corpus run."""
    collection_name: str
    n_documents_processed: int = 0
    n_documents_skipped: int = 0
    skipped_paths: list[str] = field(default_factory=list)
    n_chunks: int = 0
    n_chunks_with_pii: int = 0
    pii_types_found: list[str] = field(default_factory=list)
    embedding_model: str = ""
    summary: dict = field(default_factory=dict)


def ingest_corpus(
    corpus_dir: str | Path,
    embedding_model: str = "text-embedding-3-small",
    collection_name: str = COLLECTION_NAME_V2,
    use_presidio: bool = False,
    target_chunk_size: int = 500,
    max_chunk_size: int = 800,
    reset: bool = True,
) -> IngestionResult:
    """Run the full ingestion pipeline on a directory of documents.

    Args:
        corpus_dir: directory containing source documents.
        embedding_model: OpenAI model name for embeddings.
        collection_name: Qdrant collection to populate (default: capstone_chunks_v2).
        use_presidio: enable Presidio NER (requires presidio-analyzer).
        target_chunk_size: ideal chunk size in characters.
        max_chunk_size: hard ceiling for individual chunks.
        reset: if True, delete the collection first and rebuild.

    Returns:
        IngestionResult with audit trail.
    """
    corpus_path = Path(corpus_dir)
    if not corpus_path.exists():
        raise FileNotFoundError(f"Corpus directory not found: {corpus_dir}")

    result = IngestionResult(
        collection_name=collection_name,
        embedding_model=embedding_model,
    )

    # ── Step 1 — Discover + parse documents ─────────────────────────────
    all_chunks: list[Chunk] = []
    ingestion_ts = make_ingestion_timestamp()

    for doc_path in sorted(corpus_path.iterdir()):
        if not doc_path.is_file():
            continue
        if doc_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            print(f"  SKIP {doc_path.name} — unsupported extension")
            result.n_documents_skipped += 1
            result.skipped_paths.append(str(doc_path))
            continue

        print(f"  PARSE {doc_path.name} (format={detect_format(doc_path)})")
        try:
            parsed = parse_document(doc_path)
        except (ImportError, ValueError) as e:
            print(f"    ERROR parsing {doc_path.name}: {e}")
            result.n_documents_skipped += 1
            result.skipped_paths.append(str(doc_path))
            continue

        if not parsed.has_content:
            print(f"    EMPTY — likely a scanned PDF (no text layer). Skipping.")
            result.n_documents_skipped += 1
            result.skipped_paths.append(str(doc_path))
            continue

        # ── Step 2 — Chunk structure-aware ──────────────────────────────
        chunks = chunk_document(
            parsed,
            target_size=target_chunk_size,
            max_size=max_chunk_size,
        )
        print(f"    {len(chunks)} chunks produced")
        all_chunks.extend(chunks)
        result.n_documents_processed += 1

    if not all_chunks:
        print("  WARNING — no chunks produced from any document.")
        return result

    # ── Step 3 — Scrub PII ──────────────────────────────────────────────
    print(f"  SCRUBBING PII (use_presidio={use_presidio})...")
    scrub_chunks(all_chunks, use_presidio=use_presidio)
    n_with_pii = sum(1 for c in all_chunks if c.metadata.get("has_pii"))
    print(f"    {n_with_pii} / {len(all_chunks)} chunks had PII")

    # ── Step 4 — Finalize metadata schema ───────────────────────────────
    finalize_metadata(all_chunks, ingested_at=ingestion_ts)

    # ── Step 5 — Embed + upsert to Qdrant ───────────────────────────────
    print(f"  EMBEDDING {len(all_chunks)} chunks with {embedding_model}...")
    texts = [c.text for c in all_chunks]
    vectors = embed(texts, model=embedding_model)
    dim = EMBEDDING_DIMS[embedding_model]

    print(f"  UPSERTING into {collection_name} (dim={dim})...")
    _upsert_to_qdrant(
        all_chunks, vectors, embedding_model, dim, collection_name, reset,
    )

    # ── Step 6 — Summarise + return ─────────────────────────────────────
    summary = summarize_metadata(all_chunks)
    result.n_chunks = len(all_chunks)
    result.n_chunks_with_pii = n_with_pii
    result.pii_types_found = sorted({
        t for c in all_chunks for t in (c.metadata.get("pii_types") or [])
    })
    result.summary = summary
    return result


# ─── Qdrant upsert (with the new metadata payload + indexes) ────────────

def _upsert_to_qdrant(
    chunks: list[Chunk],
    vectors: list[list[float]],
    embedding_model: str,
    dim: int,
    collection_name: str,
    reset: bool,
) -> None:
    """Internal — push chunks + vectors into Qdrant with full metadata.

    Creates payload indexes for every field listed in
    PAYLOAD_INDEX_FIELDS so that filtered retrieval works at query
    time. Without these indexes, Qdrant Cloud returns:

        Bad request: Index required but not found for "doc_type"
        of one of the following types: [keyword].

    The index creation is idempotent — safe to call on an existing
    collection.
    """
    from qdrant_client.http import models as qmodels
    from src.rag.qdrant_store import _get_client

    client = _get_client()
    existing = [c.name for c in client.get_collections().collections]
    if reset and collection_name in existing:
        client.delete_collection(collection_name)
        existing.remove(collection_name)
    if collection_name not in existing:
        client.create_collection(
            collection_name=collection_name,
            vectors_config=qmodels.VectorParams(
                size=dim, distance=qmodels.Distance.COSINE,
            ),
        )

    # ── Create payload indexes ──────────────────────────────────────────
    # Must happen BEFORE upsert so the indexes catch all incoming points.
    # Idempotent — `create_payload_index` on an existing index is a no-op
    # on recent qdrant-client versions, and we catch the exception on
    # older ones.
    _schema_map = {
        "keyword": qmodels.PayloadSchemaType.KEYWORD,
        "integer": qmodels.PayloadSchemaType.INTEGER,
        "float":   qmodels.PayloadSchemaType.FLOAT,
        "bool":    qmodels.PayloadSchemaType.BOOL,
        "text":    qmodels.PayloadSchemaType.TEXT,
    }
    for field_name, schema_name in PAYLOAD_INDEX_FIELDS:
        try:
            client.create_payload_index(
                collection_name=collection_name,
                field_name=field_name,
                field_schema=_schema_map[schema_name],
            )
        except Exception as e:
            # Already exists, or other transient issue — log and continue.
            msg = str(e).lower()
            if "already" not in msg:
                print(f"    note: could not index {field_name!r}: {str(e)[:120]}")

    # ── Upsert points in batches ────────────────────────────────────────
    BATCH = 64
    for i in range(0, len(chunks), BATCH):
        batch_chunks = chunks[i:i + BATCH]
        batch_vectors = vectors[i:i + BATCH]
        points = [
            qmodels.PointStruct(
                id=str(uuid.uuid4()),
                vector=vec,
                payload={
                    "text": c.text,
                    "embedding_model": embedding_model,
                    **(c.metadata if isinstance(c.metadata, dict) else {}),
                },
            )
            for c, vec in zip(batch_chunks, batch_vectors)
        ]
        client.upsert(collection_name=collection_name, points=points)
