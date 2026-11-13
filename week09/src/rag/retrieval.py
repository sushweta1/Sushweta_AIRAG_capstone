"""Advanced retrieval — BM25, dense, hybrid (RRF), and cross-encoder rerank.

Public API:
    build_bm25_index(chunks)           → BM25Okapi
    dense_retrieve(store, query, k)    → list[dict]  (W8-equivalent)
    bm25_retrieve(bm25_index, chunks, query, k) → list[dict]
    hybrid_retrieve(store, bm25_index, chunks, query, k_each, k_final, rrf_k) → list[dict]
    rerank(query, candidates, top_k)   → list[dict]
    hybrid_rerank_retrieve(store, bm25_index, chunks, query, k_candidates, top_k) → list[dict]
    load_chunks_from_qdrant(store)     → list[dict]

Design choices (locked with SME):
  * Hybrid combiner = RRF (Reciprocal Rank Fusion). No score normalisation
    needed; rank position is the signal. rrf_k=60 is the canonical constant.
  * Reranker = local cross-encoder via sentence-transformers (free, ~80 MB).
    Loaded lazily — first call downloads the model; subsequent calls reuse.
  * BM25 index is in-memory and rebuilt per Python session (~30 sec for 24
    chunks; trivial). Persistence is a production concern, not a W9 lesson.
  * Tokenizer is a simple regex (lowercase alphanumeric). English HR/IT
    corpus only — no stemming, no language detection. Adequate for the
    curriculum corpus.
"""
from __future__ import annotations

# Bootstrap before any heavy import
from src import _bootstrap  # noqa: F401

import re
from typing import Any, Optional


# ─── Module-level state for the cross-encoder ───────────────────────────
# Lazy-loaded. First rerank() call triggers the download.

CROSS_ENCODER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
_cross_encoder = None  # populated by _get_cross_encoder()


# ─── Tokenization for BM25 ──────────────────────────────────────────────

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _simple_tokenize(text: str) -> list[str]:
    """Lowercase alphanumeric tokenization. English-only.

    Deliberately simple — the BM25 lesson is about TF/IDF/length-norm,
    not tokenization. Real production would use a proper tokenizer
    (spaCy, tiktoken, language-specific).
    """
    return _TOKEN_RE.findall(text.lower())


# ─── BM25 ───────────────────────────────────────────────────────────────

def build_bm25_index(chunks: list[dict]) -> Any:
    """Build a BM25Okapi index over the given chunks.

    Args:
        chunks: list of dicts, each with at least a 'text' field.

    Returns:
        A BM25Okapi object ready for .get_scores(query_tokens).

    Raises:
        ImportError if rank-bm25 isn't installed.
    """
    try:
        from rank_bm25 import BM25Okapi
    except ImportError as e:
        raise ImportError(
            "rank-bm25 not installed. Run: pip install rank-bm25"
        ) from e

    if not chunks:
        raise ValueError("Cannot build BM25 index over zero chunks.")

    tokenized = [_simple_tokenize(c["text"]) for c in chunks]
    return BM25Okapi(tokenized)


def bm25_retrieve(
    bm25_index: Any,
    chunks: list[dict],
    query: str,
    k: int = 10,
) -> list[dict]:
    """Retrieve top-k chunks by BM25 score.

    Args:
        bm25_index: BM25Okapi object from build_bm25_index().
        chunks: the SAME chunks list used to build the index — order matters.
        query: the query string.
        k: how many top results to return.

    Returns:
        List of chunk dicts with an added 'score' field (BM25 score)
        and 'rank' field (1-indexed position).
    """
    query_tokens = _simple_tokenize(query)
    if not query_tokens:
        return []

    scores = bm25_index.get_scores(query_tokens)
    # Pair each chunk with its score, sort desc, take top k
    indexed = list(enumerate(scores))
    indexed.sort(key=lambda x: x[1], reverse=True)
    top = indexed[:k]

    results = []
    for rank, (idx, score) in enumerate(top, start=1):
        chunk = dict(chunks[idx])  # copy
        chunk["score"] = float(score)
        chunk["rank"] = rank
        results.append(chunk)
    return results


# ─── Dense (Qdrant) ─────────────────────────────────────────────────────

def dense_retrieve(
    store: Any,
    query: str,
    k: int = 10,
    filter: Optional[Any] = None,
) -> list[dict]:
    """Retrieve top-k chunks by dense cosine similarity.

    Thin wrapper around qdrant_store.retrieve() that adds a 'rank' field
    so dense and BM25 results can be merged by rank position.

    Args:
        store: QdrantStore handle.
        query: the query string.
        k: how many top results to return.
        filter: optional Qdrant filter (from src.rag.qdrant_store).

    Returns:
        List of chunk dicts with 'score' (cosine) and 'rank' (1-indexed).
    """
    from src.rag.embeddings import embed
    from src.rag.qdrant_store import retrieve

    query_embedding = embed([query], model=store.embedding_model)[0]
    hits = retrieve(store, query_embedding, k=k, filter=filter)

    for rank, hit in enumerate(hits, start=1):
        hit["rank"] = rank
    return hits


# ─── Hybrid (RRF fusion) ────────────────────────────────────────────────

def hybrid_retrieve(
    store: Any,
    bm25_index: Any,
    chunks: list[dict],
    query: str,
    k_each: int = 10,
    k_final: int = 10,
    rrf_k: int = 60,
    filter: Optional[Any] = None,
) -> list[dict]:
    """Hybrid retrieval via Reciprocal Rank Fusion.

    RRF formula: rrf_score(doc) = sum over retrievers of 1 / (rrf_k + rank)

    Where rank is the doc's 1-indexed position in that retriever's results.
    Documents that didn't appear in a retriever's top-k contribute 0
    from that retriever.

    rrf_k=60 is the canonical constant from the original RRF paper
    (Cormack et al. 2009). Larger rrf_k smooths the contributions
    of top vs lower ranks.

    Args:
        store: QdrantStore handle (for dense retrieval).
        bm25_index: BM25Okapi object (for sparse retrieval).
        chunks: the list of chunk dicts used to build bm25_index.
        query: the query string.
        k_each: how many results to pull from each retriever.
        k_final: how many fused results to return.
        rrf_k: the RRF smoothing constant.
        filter: optional Qdrant filter (passed to dense_retrieve only).

    Returns:
        List of chunk dicts with 'score' (rrf_score), 'rank' (1-indexed),
        and 'dense_rank' + 'bm25_rank' (or None if not in that retriever's
        top-k).
    """
    dense_hits = dense_retrieve(store, query, k=k_each, filter=filter)
    bm25_hits = bm25_retrieve(bm25_index, chunks, query, k=k_each)

    # Build a lookup: (source, text_prefix) → record
    # Using (source, text[:100]) as the dedup key — same chunk if both match.
    fused: dict[tuple[str, str], dict] = {}

    for hit in dense_hits:
        key = (hit.get("source", ""), hit.get("text", "")[:100])
        contribution = 1.0 / (rrf_k + hit["rank"])
        fused.setdefault(key, {**hit, "rrf_score": 0.0,
                                "dense_rank": None, "bm25_rank": None})
        fused[key]["rrf_score"] += contribution
        fused[key]["dense_rank"] = hit["rank"]

    for hit in bm25_hits:
        key = (hit.get("source", ""), hit.get("text", "")[:100])
        contribution = 1.0 / (rrf_k + hit["rank"])
        if key not in fused:
            fused[key] = {**hit, "rrf_score": 0.0,
                          "dense_rank": None, "bm25_rank": None}
        fused[key]["rrf_score"] += contribution
        fused[key]["bm25_rank"] = hit["rank"]

    # Sort by RRF score desc, take top k_final
    ranked = sorted(fused.values(), key=lambda r: r["rrf_score"], reverse=True)
    top = ranked[:k_final]

    for rank, hit in enumerate(top, start=1):
        hit["score"] = hit["rrf_score"]
        hit["rank"] = rank
    return top


# ─── Cross-encoder rerank ───────────────────────────────────────────────

def _get_cross_encoder():
    """Lazy-load the cross-encoder model. ~80 MB download on first call."""
    global _cross_encoder
    if _cross_encoder is None:
        try:
            from sentence_transformers import CrossEncoder
        except ImportError as e:
            raise ImportError(
                "sentence-transformers not installed. "
                "Run: pip install sentence-transformers"
            ) from e
        _cross_encoder = CrossEncoder(CROSS_ENCODER_MODEL)
    return _cross_encoder


def rerank(
    query: str,
    candidates: list[dict],
    top_k: int = 3,
) -> list[dict]:
    """Rerank a list of candidate chunks with a cross-encoder.

    The cross-encoder reads (query, candidate.text) as a single sequence
    and scores it directly — more accurate than the bi-encoder dense
    score but quadratic in candidates, so we only rerank a small pool.

    Args:
        query: the original query string.
        candidates: list of chunk dicts (from dense / bm25 / hybrid).
        top_k: how many top reranked results to return.

    Returns:
        List of top_k chunk dicts with:
          * 'score' = cross-encoder score (NEW)
          * 'rerank_score' = same as score (for clarity)
          * 'pre_rerank_rank' = the position before reranking
          * 'rank' = new 1-indexed position after reranking
    """
    if not candidates:
        return []

    model = _get_cross_encoder()
    pairs = [(query, c.get("text", "")) for c in candidates]
    scores = model.predict(pairs)

    # Attach scores and sort
    for i, c in enumerate(candidates):
        c["pre_rerank_rank"] = c.get("rank", i + 1)
        c["rerank_score"] = float(scores[i])

    reranked = sorted(candidates, key=lambda c: c["rerank_score"], reverse=True)
    top = reranked[:top_k]

    for rank, c in enumerate(top, start=1):
        c["score"] = c["rerank_score"]
        c["rank"] = rank
    return top


# ─── Composed: hybrid + rerank in one call ──────────────────────────────

def hybrid_rerank_retrieve(
    store: Any,
    bm25_index: Any,
    chunks: list[dict],
    query: str,
    k_candidates: int = 20,
    top_k: int = 3,
    rrf_k: int = 60,
    filter: Optional[Any] = None,
) -> list[dict]:
    """End-to-end: hybrid retrieval → cross-encoder rerank → top_k.

    This is the composed function ask_rag will call when
    retrieval_method='hybrid_rerank'.

    Args:
        store: QdrantStore handle.
        bm25_index: BM25Okapi index over `chunks`.
        chunks: chunk list backing bm25_index.
        query: query string.
        k_candidates: how many candidates to pull from hybrid (then rerank).
        top_k: how many to return after reranking.
        rrf_k: RRF smoothing constant.
        filter: optional Qdrant filter (passed to hybrid).

    Returns:
        List of top_k chunk dicts with full rank lineage.
    """
    candidates = hybrid_retrieve(
        store=store, bm25_index=bm25_index, chunks=chunks,
        query=query, k_each=k_candidates // 2, k_final=k_candidates,
        rrf_k=rrf_k, filter=filter,
    )
    return rerank(query=query, candidates=candidates, top_k=top_k)


# ─── Helper: pull all chunks out of Qdrant ──────────────────────────────

def load_chunks_from_qdrant(store: Any) -> list[dict]:
    """Scroll through a Qdrant collection and return all chunk payloads.

    Used to build the BM25 index — we need every chunk in memory.
    For larger corpora (>10k chunks) this is fine; for production
    you'd persist the BM25 index separately.

    Returns:
        List of dicts matching the qdrant_store.retrieve() shape.
    """
    chunks: list[dict] = []
    offset = None
    BATCH = 256

    while True:
        response = store.client.scroll(
            collection_name=store.collection_name,
            limit=BATCH,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        points, next_offset = response
        for point in points:
            payload = point.payload or {}
            chunks.append({
                "text": payload.get("text", ""),
                "source": payload.get("source", "unknown"),
                "doc_title": payload.get("doc_title", ""),
                "section_path": payload.get("section_path", ""),
                "page": payload.get("page"),
                "doc_type": payload.get("doc_type", ""),
                "has_pii": payload.get("has_pii", False),
                "qdrant_id": str(point.id),
            })
        if next_offset is None:
            break
        offset = next_offset

    return chunks
