"""Week 10 semantic cache regression tests."""

import pytest

from src.rag.cache import (
    SemanticCache,
    cosine_similarity,
    cache_key,
)


SCOPE = "v2.w10|dense|k3|gpt-4o-mini"

RESPONSE = {
    "answer": "Annual leave is 25 days.",
    "sources": ["leave_policy.md"],
    "citations": [
        {
            "source": "leave_policy.md",
            "section_path": "Annual Leave",
        }
    ],
}


@pytest.fixture
def cache(tmp_path):
    c = SemanticCache(str(tmp_path / "test.db"))
    yield c
    c.close()


def test_default_threshold(cache):
    assert cache.threshold == 0.95


def test_cosine_identical():
    assert cosine_similarity([1, 0], [1, 0]) == pytest.approx(1)


def test_cosine_unrelated():
    assert cosine_similarity([1, 0], [0, 1]) == pytest.approx(0)


def test_cosine_zero_vector():
    assert cosine_similarity([0, 0], [1, 0]) == -1


def test_cosine_dimension_mismatch():
    assert cosine_similarity([1, 0], [1, 0, 0]) == -1


def test_cache_key_scope_isolation():
    assert cache_key("question", "v1") != cache_key("question", "v2")


def test_exact_cache_hit(cache):
    cache.put("What is annual leave?", [1, 0], RESPONSE, SCOPE)

    hit = cache.lookup_exact("What is annual leave?", SCOPE)

    assert hit["match_type"] == "exact"
    assert hit["response"] == RESPONSE


def test_exact_cache_miss(cache):
    assert cache.lookup_exact("Unknown question", SCOPE) is None


def test_semantic_cache_hit(cache):
    cache.put("What is annual leave?", [1, 0], RESPONSE, SCOPE)

    hit = cache.lookup(
        "Tell me about annual leave",
        [0.99, 0.01],
        SCOPE,
    )

    assert hit is not None
    assert hit["match_type"] == "semantic"
    assert hit["similarity"] >= 0.95
    assert hit["response"] == RESPONSE


def test_semantic_cache_miss(cache):
    cache.put("Annual leave", [1, 0], RESPONSE, SCOPE)

    assert cache.lookup("VPN setup", [0, 1], SCOPE) is None


def test_identifier_guard(cache):
    cache.put("Explain AC-1042", [1, 0], RESPONSE, SCOPE)

    # Even identical vectors must not bypass identifier protection.
    assert cache.lookup("Explain AC-4408", [1, 0], SCOPE) is None


def test_numeric_guard(cache):
    cache.put("Leave policy 2025", [1, 0], RESPONSE, SCOPE)

    assert cache.lookup("Leave policy 2026", [1, 0], SCOPE) is None


def test_kb_version_isolation(cache):
    cache.put("Annual leave", [1, 0], RESPONSE, "v1")

    assert cache.lookup_exact("Annual leave", "v2") is None
    assert cache.lookup("Annual leave", [1, 0], "v2") is None


def test_configuration_isolation(cache):
    cache.put("Annual leave", [1, 0], RESPONSE, "dense-k3")

    assert cache.lookup_exact("Annual leave", "dense-k5") is None


def test_cache_clear(cache):
    cache.put("Annual leave", [1, 0], RESPONSE, SCOPE)

    assert cache.clear() == 1
    assert cache.lookup_exact("Annual leave", SCOPE) is None
    assert cache.stats()["entries"] == 0


def test_cache_statistics(cache):
    cache.put("Annual leave", [1, 0], RESPONSE, SCOPE)

    cache.lookup_exact("Annual leave", SCOPE)
    cache.lookup("Leave entitlement", [1, 0], SCOPE)
    cache.lookup("VPN setup", [0, 1], SCOPE)

    stats = cache.stats()

    assert stats["exact_hits"] == 1
    assert stats["semantic_hits"] == 1
    assert stats["misses"] == 1
    assert stats["hit_rate"] == pytest.approx(2 / 3)


def test_persistence(tmp_path):
    path = str(tmp_path / "persistent.db")

    first = SemanticCache(path)
    first.put("Annual leave", [1, 0], RESPONSE, SCOPE)
    first.close()

    second = SemanticCache(path)

    assert second.lookup_exact(
        "Annual leave", SCOPE
    )["response"] == RESPONSE

    second.close()


def test_invalid_threshold():
    with pytest.raises(ValueError):
        SemanticCache(":memory:", threshold=1.5)
