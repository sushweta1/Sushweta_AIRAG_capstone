"""Migrate the Week 6 JSON embedding index into Qdrant Cloud."""

import json
from pathlib import Path

from src.rag.qdrant_store import (
    load_store,
    ensure_collection,
    upsert_chunks,
    collection_size,
)

INDEX_PATH = Path("data/embeddings.json")


def main():
    if not INDEX_PATH.exists():
        raise FileNotFoundError(
            f"Missing {INDEX_PATH}. Run python -m scripts.build_index first."
        )

    print("Loading Week 6 embedding index...")

    with INDEX_PATH.open(encoding="utf-8") as f:
        index = json.load(f)

    chunks = []
    vectors = []

    for item in index:
        chunks.append({
            "chunk_id": item["chunk_id"],
            "source_id": item["source_id"],
            "text": item["text"],
        })
        vectors.append(item["vector"])

    print(f"Loaded {len(chunks)} chunks.")

    if not all(len(vector) == 1536 for vector in vectors):
        raise ValueError("Expected 1536-dimensional embeddings.")

    print("Connecting to Qdrant Cloud...")

    store = load_store()
    ensure_collection(store)

    print(f"Uploading {len(chunks)} vectors...")
    upsert_chunks(store, chunks, vectors)

    print("Migration complete!")
    print("Collection:", store.collection)
    print("Total points:", collection_size(store))


if __name__ == "__main__":
    main()
