"""Qdrant vector store for the FastAPI Knowledge Assistant."""

import os
from dataclasses import dataclass

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

COLLECTION_NAME = "capstone_chunks"
EMBEDDING_DIM = 1536


@dataclass
class QdrantStore:
    client: QdrantClient
    collection: str


def load_store() -> QdrantStore:
    client = QdrantClient(
        url=os.environ["QDRANT_URL"],
        api_key=os.environ["QDRANT_API_KEY"],
    )
    return QdrantStore(client=client, collection=COLLECTION_NAME)


def ensure_collection(store: QdrantStore) -> None:
    if not store.client.collection_exists(store.collection):
        store.client.create_collection(
            collection_name=store.collection,
            vectors_config=VectorParams(
                size=EMBEDDING_DIM,
                distance=Distance.COSINE,
            ),
        )


def upsert_chunks(
    store: QdrantStore,
    chunks: list[dict],
    vectors: list[list[float]],
) -> None:
    if len(chunks) != len(vectors):
        raise ValueError("Chunk and vector counts must match")

    points = [
        PointStruct(
            id=i,
            vector=vector,
            payload={
                "chunk_id": chunk["chunk_id"],
                "source_id": chunk["source_id"],
                "text": chunk["text"],
            },
        )
        for i, (chunk, vector) in enumerate(zip(chunks, vectors))
    ]

    for start in range(0, len(points), 100):
        store.client.upsert(
            collection_name=store.collection,
            points=points[start:start + 100],
            wait=True,
        )


def collection_size(store: QdrantStore) -> int:
    return store.client.get_collection(store.collection).points_count
