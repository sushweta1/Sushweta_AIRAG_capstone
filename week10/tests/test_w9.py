"""W9 smoke tests — retrieval.py + qdrant_rag.py shape checks.

Run with: python -m pytest tests/ -v
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import _bootstrap  # noqa: F401

import pytest

from src.rag.retrieval import (
    _simple_tokenize,
    build_bm25_index,
    bm25_retrieve,
    rerank,
    CROSS_ENCODER_MODEL,
)
from src.rag.qdrant_rag import VALID_METHODS, ask_rag


# ─── Tokenizer ──────────────────────────────────────────────────────────

def test_tokenize_basic():
    tokens = _simple_tokenize("Hello, World!")
    assert tokens == ["hello", "world"]


def test_tokenize_with_punctuation_and_numbers():
    tokens = _simple_tokenize("Email me at alice@example.com — 2024 only.")
    assert "alice" in tokens
    assert "example" in tokens
    assert "com" in tokens
    assert "2024" in tokens


def test_tokenize_empty_returns_empty_list():
    assert _simple_tokenize("") == []
    assert _simple_tokenize("...!!!???") == []


# ─── BM25 ───────────────────────────────────────────────────────────────

CHUNKS = [
    {"text": "Annual leave entitlement is 25 days per year", "source": "leave.md"},
    {"text": "VPN setup requires Cisco AnyConnect client", "source": "vpn.md"},
    {"text": "Sick leave needs a medical certificate after 3 days", "source": "leave.md"},
    {"text": "Performance review happens annually in March", "source": "perf.md"},
]


def test_bm25_index_builds():
    idx = build_bm25_index(CHUNKS)
    assert idx is not None
    # rank-bm25's BM25Okapi has .get_scores
    assert hasattr(idx, "get_scores")


def test_bm25_index_zero_chunks_raises():
    with pytest.raises(ValueError):
        build_bm25_index([])


def test_bm25_retrieve_returns_top_k():
    idx = build_bm25_index(CHUNKS)
    hits = bm25_retrieve(idx, CHUNKS, "leave policy", k=2)
    assert len(hits) == 2
    assert all("rank" in h for h in hits)
    assert all("score" in h for h in hits)


def test_bm25_retrieve_relevant_first():
    """Use a discriminating term: 'cisco' only appears in vpn.md."""
    idx = build_bm25_index(CHUNKS)
    hits = bm25_retrieve(idx, CHUNKS, "cisco", k=4)
    assert hits[0]["source"] == "vpn.md"


def test_bm25_retrieve_empty_query_returns_empty():
    idx = build_bm25_index(CHUNKS)
    hits = bm25_retrieve(idx, CHUNKS, "???!!!", k=3)
    assert hits == []


# ─── RRF fusion via hybrid_retrieve (using in-memory Qdrant) ────────────

def test_hybrid_retrieve_with_inmemory_qdrant(monkeypatch):
    """End-to-end test: in-memory Qdrant + BM25 + RRF fusion."""
    try:
        from qdrant_client import QdrantClient
        from qdrant_client.http import models as qmodels
    except ImportError:
        pytest.skip("qdrant-client not installed")

    # Set up an in-memory Qdrant with 4 chunks
    client = QdrantClient(":memory:")
    client.create_collection(
        collection_name="t",
        vectors_config=qmodels.VectorParams(size=4, distance=qmodels.Distance.COSINE),
    )
    # Deterministic vectors — 4 dim, each chunk a different one-hot-ish
    vectors = [
        [1.0, 0.1, 0.0, 0.0],  # leave annual
        [0.0, 1.0, 0.0, 0.0],  # vpn
        [1.0, 0.0, 0.1, 0.0],  # sick leave
        [0.0, 0.0, 0.0, 1.0],  # perf
    ]
    client.upsert(
        collection_name="t",
        points=[
            qmodels.PointStruct(id=i, vector=v,
                                  payload={"text": c["text"], "source": c["source"]})
            for i, (c, v) in enumerate(zip(CHUNKS, vectors))
        ],
    )

    # Stub the embed() function to return a fixed query embedding
    from src.rag import retrieval, qdrant_store

    class FakeStore:
        def __init__(self):
            self.client = client
            self.collection_name = "t"
            self.embedding_model = "fake-model"
            self.dim = 4

    monkeypatch.setattr("src.rag.embeddings.embed",
                         lambda texts, model: [[1.0, 0.0, 0.0, 0.0]] * len(texts))

    bm25_idx = build_bm25_index(CHUNKS)
    from src.rag.retrieval import hybrid_retrieve
    hits = hybrid_retrieve(
        store=FakeStore(),
        bm25_index=bm25_idx,
        chunks=CHUNKS,
        query="leave",
        k_each=4,
        k_final=3,
    )
    assert len(hits) <= 3
    # Top result should have an RRF score > 0
    assert hits[0]["score"] > 0
    # Top result should expose rank lineage
    assert "dense_rank" in hits[0] or "bm25_rank" in hits[0]


# ─── ask_rag dispatch validation ────────────────────────────────────────

def test_ask_rag_validates_method():
    """Bad retrieval_method should raise ValueError before any API call."""
    with pytest.raises(ValueError):
        ask_rag("test", store=None, retrieval_method="invalid_method")


def test_ask_rag_hybrid_requires_bm25_and_chunks():
    """hybrid method without bm25_index should raise."""
    with pytest.raises(ValueError):
        ask_rag("test", store=None, retrieval_method="hybrid")


def test_ask_rag_hybrid_rerank_requires_bm25_and_chunks():
    """hybrid_rerank method without bm25_index should raise."""
    with pytest.raises(ValueError):
        ask_rag("test", store=None, retrieval_method="hybrid_rerank")


def test_valid_methods_includes_all_three():
    assert "dense" in VALID_METHODS
    assert "hybrid" in VALID_METHODS
    assert "hybrid_rerank" in VALID_METHODS
    assert len(VALID_METHODS) == 3


# ─── Cross-encoder reference (no actual model load) ─────────────────────

def test_cross_encoder_model_name_set():
    assert CROSS_ENCODER_MODEL == "cross-encoder/ms-marco-MiniLM-L-6-v2"


def test_rerank_empty_candidates_returns_empty():
    """No candidates → no rerank needed (and no model load)."""
    assert rerank("query", [], top_k=3) == []


# ─── Query rewrite imports ──────────────────────────────────────────────

def test_query_rewrite_module_imports():
    from src.rag.query_rewrite import (
        hyde_rewrite, multi_query_rewrite, step_back_rewrite,
        retrieve_with_rewrite, REWRITE_MODEL,
    )
    assert REWRITE_MODEL == "gpt-4o-mini"
