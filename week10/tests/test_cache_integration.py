"""Week 10 — cache-aware RAG integration tests."""

from types import SimpleNamespace

import pytest

from src.rag.cache import SemanticCache
from src.rag import qdrant_rag as rag


@pytest.fixture
def setup(monkeypatch, tmp_path):

    store = SimpleNamespace(
        collection_name="capstone_chunks_v10",
        embedding_model="text-embedding-3-small",
        dim=2,
    )

    cache = SemanticCache(
        str(tmp_path / "integration.db")
    )

    calls = {"embed": 0, "rag": 0}

    def fake_embed(texts, model):
        calls["embed"] += 1
        return [[1.0, 0.0] for _ in texts]

    def fake_rag(**kwargs):
        calls["rag"] += 1

        return {
            "answer": "Annual leave is 25 days.",
            "sources": ["leave_policy.md"],
            "citations": [
                {"source": "leave_policy.md"}
            ],
            "cost_usd": 0.001,
            "prompt_tokens": 100,
            "completion_tokens": 20,
        }

    monkeypatch.setattr(rag, "embed", fake_embed)
    monkeypatch.setattr(
        rag,
        "_ask_rag_uncached",
        fake_rag,
    )

    yield store, cache, calls

    cache.close()


def test_cold_request(setup):
    store, cache, calls = setup

    result = rag.ask_rag(
        "Annual leave", store, cache=cache
    )

    assert result["cache_hit"] is False
    assert result["cache_match"] == "miss"
    assert calls == {"embed": 1, "rag": 1}
    assert cache.stats()["entries"] == 1


def test_exact_hit_bypasses_pipeline(setup):
    store, cache, calls = setup

    cold = rag.ask_rag(
        "Annual leave", store, cache=cache
    )

    warm = rag.ask_rag(
        "Annual leave", store, cache=cache
    )

    assert warm["cache_hit"] is True
    assert warm["cache_match"] == "exact"
    assert warm["answer"] == cold["answer"]
    assert warm["citations"] == cold["citations"]
    assert warm["cost_usd"] == 0
    assert warm["prompt_tokens"] == 0
    assert calls == {"embed": 1, "rag": 1}


def test_semantic_hit_bypasses_generation(setup):
    store, cache, calls = setup

    rag.ask_rag(
        "Annual leave", store, cache=cache
    )

    result = rag.ask_rag(
        "Tell me about annual leave",
        store,
        cache=cache,
    )

    assert result["cache_hit"] is True
    assert result["cache_match"] == "semantic"
    assert calls == {"embed": 2, "rag": 1}


def test_version_change_causes_miss(setup):
    store, cache, calls = setup

    rag.ask_rag(
        "Annual leave",
        store,
        cache=cache,
        kb_version="v1",
    )

    result = rag.ask_rag(
        "Annual leave",
        store,
        cache=cache,
        kb_version="v2",
    )

    assert result["cache_hit"] is False
    assert calls["rag"] == 2


def test_k_change_causes_miss(setup):
    store, cache, calls = setup

    rag.ask_rag(
        "Annual leave", store, k=3, cache=cache
    )

    result = rag.ask_rag(
        "Annual leave", store, k=5, cache=cache
    )

    assert result["cache_hit"] is False
    assert calls["rag"] == 2


def test_scope_change_causes_miss(setup):
    store, cache, calls = setup

    rag.ask_rag(
        "Annual leave",
        store,
        cache=cache,
        cache_scope="scope-a",
    )

    result = rag.ask_rag(
        "Annual leave",
        store,
        cache=cache,
        cache_scope="scope-b",
    )

    assert result["cache_hit"] is False
    assert calls["rag"] == 2


def test_filtered_request_bypasses_cache(setup):
    store, cache, calls = setup

    result = rag.ask_rag(
        "Annual leave",
        store,
        filter={"example": "hr"},
        cache=cache,
    )

    assert result["cache_match"] == "disabled"
    assert cache.stats()["entries"] == 0


def test_no_cache_backward_compatible(setup):
    store, cache, calls = setup

    result = rag.ask_rag(
        "Annual leave", store
    )

    assert result["cache_match"] == "disabled"
    assert result["answer"] == "Annual leave is 25 days."


def test_cache_clear_forces_new_generation(setup):
    store, cache, calls = setup

    rag.ask_rag(
        "Annual leave", store, cache=cache
    )

    cache.clear()

    result = rag.ask_rag(
        "Annual leave", store, cache=cache
    )

    assert result["cache_hit"] is False
    assert calls["rag"] == 2
