"""Week 10 — Document replacement integration tests."""

from types import SimpleNamespace

import pytest
from qdrant_client import QdrantClient, models

from src.ingest.pipeline import update_document
from src.rag.cache import SemanticCache
from src.rag.kb_version import get_kb_version
from src.rag.qdrant_store import live_filter
from src.rag.retrieval import load_chunks_from_qdrant


@pytest.fixture
def setup(tmp_path, monkeypatch):

    client = QdrantClient(":memory:")

    collection = "capstone_chunks_v10"

    client.create_collection(
        collection_name=collection,
        vectors_config=models.VectorParams(
            size=3,
            distance=models.Distance.COSINE,
        ),
    )

    client.upsert(
        collection_name=collection,
        points=[
            models.PointStruct(
                id=1,
                vector=[1.0, 0.0, 0.0],
                payload={
                    "text": "Annual leave is 20 days.",
                    "source": "leave_policy.md",
                    "doc_type": "hr",
                    "kb_version": "v2.w10",
                },
            ),
            models.PointStruct(
                id=2,
                vector=[0.0, 1.0, 0.0],
                payload={
                    "text": "VPN requires authentication.",
                    "source": "vpn_policy.md",
                    "doc_type": "it",
                    "kb_version": "v2.w10",
                },
            ),
        ],
    )

    store = SimpleNamespace(
        client=client,
        collection_name=collection,
        embedding_model="fake-model",
        dim=3,
    )

    cache = SemanticCache(
        str(tmp_path / "responses.db")
    )

    cache.put(
        "What is annual leave?",
        [1.0, 0.0, 0.0],
        {"answer": "20 days"},
        scope="lifecycle-test",
    )

    document = tmp_path / "leave_policy.md"

    document.write_text(
        "# Leave Policy\n\n"
        "## Annual Leave\n\n"
        "All full-time employees receive "
        "25 working days of paid annual leave "
        "per calendar year.\n",
        encoding="utf-8",
    )

    version_path = tmp_path / "kb_version.json"

    monkeypatch.setattr(
        "src.ingest.pipeline.embed",
        lambda texts, model: [
            [1.0, 0.0, 0.0] for _ in texts
        ],
    )

    yield SimpleNamespace(
        store=store,
        cache=cache,
        document=document,
        version_path=version_path,
    )

    cache.close()
    client.close()


def run_update(setup):

    return update_document(
        document_path=setup.document,
        store=setup.store,
        cache=setup.cache,
        version_path=setup.version_path,
    )


def test_successful_document_replacement(setup):

    result = run_update(setup)

    assert result["status"] == "success"
    assert result["old_chunks_tombstoned"] == 1
    assert result["new_chunks_inserted"] >= 1

    assert (
        result["new_chunks_inserted"]
        == result["live_chunks_verified"]
    )

    chunks = load_chunks_from_qdrant(setup.store)

    assert any(
        "25 working days" in c["text"]
        for c in chunks
    )

    assert all(
        "20 days" not in c["text"]
        for c in chunks
    )


def test_old_document_retained_as_tombstone(setup):

    run_update(setup)

    points = setup.store.client.retrieve(
        collection_name=setup.store.collection_name,
        ids=[1],
        with_payload=True,
    )

    assert len(points) == 1
    assert points[0].payload["deleted_at"] > 0
    assert "20 days" in points[0].payload["text"]


def test_unrelated_document_preserved(setup):

    run_update(setup)

    chunks = load_chunks_from_qdrant(setup.store)

    assert any(
        c["source"] == "vpn_policy.md"
        for c in chunks
    )


def test_cache_invalidated_after_update(setup):

    assert setup.cache.stats()["entries"] == 1

    result = run_update(setup)

    assert result["cache_entries_cleared"] >= 1
    assert setup.cache.stats()["entries"] == 0

    assert setup.cache.lookup_exact(
        "What is annual leave?",
        scope="lifecycle-test",
    ) is None


def test_kb_version_incremented(setup):

    result = run_update(setup)

    assert result["previous_kb_version"] == "v2.w10"
    assert result["kb_version"] == "v2.w10.1"

    assert (
        get_kb_version(setup.version_path)
        == "v2.w10.1"
    )


def test_second_update_increments_version(setup):

    run_update(setup)

    setup.document.write_text(
        "# Leave Policy\n\n"
        "## Annual Leave\n\n"
        "All full-time employees receive "
        "30 working days of paid annual leave.\n",
        encoding="utf-8",
    )

    result = run_update(setup)

    assert result["kb_version"] == "v2.w10.2"

    chunks = load_chunks_from_qdrant(setup.store)

    assert any(
        "30 working days" in c["text"]
        for c in chunks
    )

    assert all(
        "25 working days" not in c["text"]
        for c in chunks
    )


def test_embedding_failure_preserves_document(
    setup, monkeypatch
):

    def fail_embedding(*args, **kwargs):
        raise RuntimeError("Simulated embedding failure")

    monkeypatch.setattr(
        "src.ingest.pipeline.embed",
        fail_embedding,
    )

    with pytest.raises(
        RuntimeError,
        match="Simulated embedding failure",
    ):
        run_update(setup)

    chunks = load_chunks_from_qdrant(setup.store)

    assert any(
        "20 days" in c["text"]
        for c in chunks
    )

    assert setup.cache.stats()["entries"] == 1

    assert (
        get_kb_version(setup.version_path)
        == "v2.w10"
    )


def test_upsert_failure_rolls_back(
    setup, monkeypatch
):

    def fail_upsert(*args, **kwargs):
        raise RuntimeError("Simulated upsert failure")

    monkeypatch.setattr(
        setup.store.client,
        "upsert",
        fail_upsert,
    )

    with pytest.raises(
        RuntimeError,
        match="rollback completed",
    ):
        run_update(setup)

    chunks = load_chunks_from_qdrant(setup.store)

    assert any(
        "20 days" in c["text"]
        for c in chunks
    )

    assert all(
        "25 working days" not in c["text"]
        for c in chunks
    )

    assert (
        get_kb_version(setup.version_path)
        == "v2.w10"
    )
