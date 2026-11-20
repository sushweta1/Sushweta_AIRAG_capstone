"""Week 10 — Knowledge base lifecycle regression tests."""

from types import SimpleNamespace

import pytest
from qdrant_client import QdrantClient, models

from src.rag.qdrant_store import live_filter, retrieve
from src.rag.retrieval import (
    build_bm25_index,
    hybrid_retrieve,
    load_chunks_from_qdrant,
)


@pytest.fixture
def store(monkeypatch):

    client = QdrantClient(":memory:")

    client.create_collection(
        collection_name="lifecycle_test",
        vectors_config=models.VectorParams(
            size=3,
            distance=models.Distance.COSINE,
        ),
    )

    documents = [
        {
            "text": "Annual leave entitlement is 20 days.",
            "source": "leave_policy.md",
            "doc_type": "hr",
            "deleted_at": 1794677210.0,
        },
        {
            "text": "Annual leave entitlement is 25 days.",
            "source": "leave_policy.md",
            "doc_type": "hr",
        },
        {
            "text": "Employees receive public holidays.",
            "source": "holiday_policy.md",
            "doc_type": "hr",
            "deleted_at": None,
        },
        {
            "text": "VPN access requires authentication.",
            "source": "vpn_policy.md",
            "doc_type": "it",
        },
    ]

    client.upsert(
        collection_name="lifecycle_test",
        points=[
            models.PointStruct(
                id=i,
                vector=[1.0, 0.0, 0.0],
                payload=doc,
            )
            for i, doc in enumerate(documents, 1)
        ],
    )

    monkeypatch.setattr(
        "src.rag.embeddings.embed",
        lambda texts, model: [
            [1.0, 0.0, 0.0] for _ in texts
        ],
    )

    yield SimpleNamespace(
        client=client,
        collection_name="lifecycle_test",
        embedding_model="fake-model",
        dim=3,
        original_chunks=documents,
    )

    client.close()


def metadata_filter(value):
    return models.Filter(
        must=[
            models.FieldCondition(
                key="doc_type",
                match=models.MatchValue(value=value),
            )
        ]
    )


def test_live_count_excludes_tombstones(store):

    count = store.client.count(
        collection_name=store.collection_name,
        count_filter=live_filter(),
        exact=True,
    ).count

    assert count == 3


def test_missing_deleted_at_is_live(store):

    chunks = load_chunks_from_qdrant(store)

    assert any(
        "25 days" in c["text"] for c in chunks
    )


def test_null_deleted_at_is_live(store):

    chunks = load_chunks_from_qdrant(store)

    assert any(
        c["source"] == "holiday_policy.md"
        for c in chunks
    )


def test_loader_excludes_deleted_chunks(store):

    chunks = load_chunks_from_qdrant(store)

    assert len(chunks) == 3
    assert all(
        "20 days" not in c["text"] for c in chunks
    )


def test_loader_preserves_metadata_filter(store):

    chunks = load_chunks_from_qdrant(
        store,
        filter=metadata_filter("hr"),
    )

    assert len(chunks) == 2
    assert all(
        c["doc_type"] == "hr" for c in chunks
    )


def test_dense_excludes_tombstones(store):

    hits = retrieve(
        store,
        [1.0, 0.0, 0.0],
        k=10,
    )

    assert len(hits) == 3
    assert all(
        "20 days" not in h["text"] for h in hits
    )


def test_dense_preserves_metadata_filter(store):

    hits = retrieve(
        store,
        [1.0, 0.0, 0.0],
        k=10,
        filter=metadata_filter("hr"),
    )

    assert len(hits) == 2
    assert all(
        h["doc_type"] == "hr" for h in hits
    )


def test_hybrid_rejects_stale_bm25_index(store):

    stale_chunks = store.original_chunks
    stale_index = build_bm25_index(stale_chunks)

    hits = hybrid_retrieve(
        store=store,
        bm25_index=stale_index,
        chunks=stale_chunks,
        query="Annual leave entitlement 20 days",
        k_each=10,
        k_final=10,
    )

    assert hits
    assert all(
        "20 days" not in h["text"] for h in hits
    )
    assert any(
        "25 days" in h["text"] for h in hits
    )


def test_hybrid_preserves_metadata_filter(store):

    chunks = store.original_chunks

    hits = hybrid_retrieve(
        store=store,
        bm25_index=build_bm25_index(chunks),
        chunks=chunks,
        query="Annual leave VPN access",
        k_each=10,
        k_final=10,
        filter=metadata_filter("hr"),
    )

    assert len(hits) == 2
    assert all(
        h["doc_type"] == "hr" for h in hits
    )
    assert all(
        "20 days" not in h["text"] for h in hits
    )


def test_hybrid_handles_empty_filtered_corpus(store):

    chunks = store.original_chunks

    hits = hybrid_retrieve(
        store=store,
        bm25_index=build_bm25_index(chunks),
        chunks=chunks,
        query="Annual leave",
        filter=metadata_filter("nonexistent"),
    )

    assert hits == []


def test_new_tombstone_invalidates_stale_index(store):

    chunks = load_chunks_from_qdrant(store)
    stale_index = build_bm25_index(chunks)

    # Tombstone the current annual leave policy
    # AFTER the BM25 index has been created.

    store.client.set_payload(
        collection_name=store.collection_name,
        payload={"deleted_at": 1794677300.0},
        points=[2],
        wait=True,
    )

    hits = hybrid_retrieve(
        store=store,
        bm25_index=stale_index,
        chunks=chunks,
        query="Annual leave entitlement",
        k_each=10,
        k_final=10,
    )

    assert all(
        h["source"] != "leave_policy.md"
        for h in hits
    )
