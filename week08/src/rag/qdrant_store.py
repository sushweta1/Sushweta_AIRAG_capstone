"""Qdrant vector store — W8 reference implementation.

Extends W7's qdrant_store with metadata filter support. The new
retrieve() signature accepts an optional `filter` parameter that
gets passed straight to Qdrant's query_points() — letting the W9
hybrid story build on this naturally.

Backward compatibility: every W7 call site still works. The filter
defaults to None, which means "no filter" — identical to W7 behaviour.
"""
from __future__ import annotations

# Bootstrap before any qdrant_client / numpy import
from src import _bootstrap  # noqa: F401

import os
import uuid
from dataclasses import dataclass
from typing import Any, Optional


COLLECTION_NAME = "capstone_chunks"        # W7 baseline (kept for comparison)
COLLECTION_NAME_V2 = "capstone_chunks_v2"  # W8 — metadata-enriched


@dataclass
class QdrantStore:
    """Handle wrapping a Qdrant client + collection.

    Same shape as W7. The embedding_model is carried so we can refuse
    mismatched queries.
    """
    client: Any                  # qdrant_client.QdrantClient
    collection_name: str
    embedding_model: str
    dim: int


def _resolve_qdrant_config() -> tuple[str, str | None]:
    """Return (url, api_key) from QDRANT_URL + QDRANT_API_KEY env vars."""
    url = os.environ.get("QDRANT_URL", "http://localhost:6333")
    api_key = os.environ.get("QDRANT_API_KEY") or None
    return url, api_key


def _get_client():
    """Build a QdrantClient using env vars."""
    from qdrant_client import QdrantClient
    url, api_key = _resolve_qdrant_config()
    if api_key:
        return QdrantClient(url=url, api_key=api_key)
    return QdrantClient(url=url)


def build_store(chunks, embeddings, embedding_model: str, dim: int,
                collection_name: str = COLLECTION_NAME,
                reset: bool = True) -> QdrantStore:
    """Build (or rebuild) a Qdrant collection from chunks + embeddings.

    Note: for the W8 metadata-enriched pipeline, use
    `src.ingest.pipeline.ingest_corpus()` instead — it handles the
    full pipeline. This function is the W7-compatible legacy path
    kept for backward compatibility.
    """
    from qdrant_client.http import models as qmodels

    if len(chunks) != len(embeddings):
        raise ValueError(
            f"chunks ({len(chunks)}) and embeddings ({len(embeddings)}) "
            f"must have the same length"
        )

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

    BATCH = 64
    for i in range(0, len(chunks), BATCH):
        batch_chunks = chunks[i:i + BATCH]
        batch_vectors = embeddings[i:i + BATCH]
        points = [
            qmodels.PointStruct(
                id=str(uuid.uuid4()),
                vector=vec,
                payload={
                    "text": c.text,
                    "source": c.source,
                    "embedding_model": embedding_model,
                    # W8: include metadata if present on chunk
                    **(c.metadata if hasattr(c, "metadata") and
                        isinstance(c.metadata, dict) else {}),
                },
            )
            for c, vec in zip(batch_chunks, batch_vectors)
        ]
        client.upsert(collection_name=collection_name, points=points)

    return QdrantStore(
        client=client,
        collection_name=collection_name,
        embedding_model=embedding_model,
        dim=dim,
    )


def load_store(collection_name: str = COLLECTION_NAME_V2,
               embedding_model: str = "text-embedding-3-small",
               dim: int = 1536) -> QdrantStore:
    """Open an existing Qdrant collection.

    Default collection_name changed from W7: now points at
    capstone_chunks_v2 (the metadata-enriched one).
    """
    client = _get_client()
    existing = [c.name for c in client.get_collections().collections]
    if collection_name not in existing:
        raise RuntimeError(
            f"Collection {collection_name!r} doesn't exist. "
            f"Run scripts/ingest_corpus.py first."
        )
    return QdrantStore(
        client=client,
        collection_name=collection_name,
        embedding_model=embedding_model,
        dim=dim,
    )


def retrieve(store: QdrantStore, query_embedding: list[float],
             k: int = 3,
             filter: Optional[Any] = None) -> list:
    """Return top-k chunks by cosine similarity, optionally filtered.

    NEW in W8 — the `filter` parameter accepts a Qdrant Filter
    object. Pass None (default) for the W7-equivalent unfiltered behaviour.

    Filter examples (from src.rag.qdrant_filters):
        filter=eq("doc_type", "hr")
        filter=combine_and(eq("doc_type", "hr"), eq("has_pii", False))

    Returns a list of dicts: {text, source, doc_title, ..., score}.
    The caller decides how much of the payload to use — the W8 RAG
    pipeline only needs text + source, but lab activities may want
    section_path + page for citations.
    """
    response = store.client.query_points(
        collection_name=store.collection_name,
        query=query_embedding,
        limit=k,
        query_filter=filter,
    )
    results = []
    for hit in response.points:
        payload = hit.payload or {}
        results.append({
            "text": payload.get("text", ""),
            "source": payload.get("source", "unknown"),
            "doc_title": payload.get("doc_title", ""),
            "section_path": payload.get("section_path", ""),
            "page": payload.get("page"),
            "doc_type": payload.get("doc_type", ""),
            "has_pii": payload.get("has_pii", False),
            "score": float(hit.score) if hit.score is not None else 0.0,
        })
    return results


def collection_count(store: QdrantStore) -> int:
    """Return how many points are in the collection."""
    info = store.client.get_collection(store.collection_name)
    return info.points_count


# ─── Filter helpers (the Qdrant DSL) ────────────────────────────────────

def eq(field: str, value: Any):
    """Build a single equality condition: payload.field == value.

    Example:
        eq("doc_type", "hr")
    """
    from qdrant_client.http import models as qmodels
    return qmodels.Filter(
        must=[qmodels.FieldCondition(
            key=field, match=qmodels.MatchValue(value=value),
        )],
    )


def combine_and(*filters):
    """Combine multiple filters with AND semantics.

    Example:
        combine_and(eq("doc_type", "hr"), eq("has_pii", False))
    """
    from qdrant_client.http import models as qmodels
    all_conditions = []
    for f in filters:
        if f and f.must:
            all_conditions.extend(f.must)
    return qmodels.Filter(must=all_conditions)


def combine_or(*filters):
    """Combine multiple filters with OR semantics."""
    from qdrant_client.http import models as qmodels
    any_conditions = []
    for f in filters:
        if f and f.must:
            any_conditions.extend(f.must)
    return qmodels.Filter(should=any_conditions)
