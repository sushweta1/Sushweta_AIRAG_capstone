"""Migrate the W6 JSON cache into a Qdrant collection.

This is the heart of W7 Lab Step 1. Read W6's data/embeddings.json
(populated by scripts/build_index.py), and upsert into a Qdrant
collection.

Usage:
    # Local Docker (default)
    export QDRANT_URL=http://localhost:6333
    python scripts/migrate_to_qdrant.py

    # Qdrant Cloud
    export QDRANT_URL=https://YOUR-CLUSTER.cloud.qdrant.io
    export QDRANT_API_KEY=...
    python scripts/migrate_to_qdrant.py

    # Pick a specific embedding model (must match the cache)
    python scripts/migrate_to_qdrant.py --model text-embedding-3-large
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import _bootstrap  # noqa: F401

import argparse

from src.rag.chunker import chunk_corpus
from src.rag.embeddings import EMBEDDING_DIMS, EMBEDDING_RATES
from src.rag.qdrant_store import COLLECTION_NAME, collection_count, migrate_from_json_cache


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate JSON cache → Qdrant.")
    parser.add_argument("--corpus", default="data/corpus")
    parser.add_argument("--cache", default="data/embeddings.json")
    parser.add_argument("--model", default="text-embedding-3-small",
                        choices=list(EMBEDDING_RATES.keys()))
    parser.add_argument("--collection", default=COLLECTION_NAME)
    parser.add_argument("--size", type=int, default=500)
    parser.add_argument("--overlap", type=int, default=50)
    args = parser.parse_args()

    cache_path = Path(args.cache)
    if not cache_path.exists():
        print(f"ERROR: cache not found at {cache_path}")
        print("Run scripts/build_index.py first to populate it.")
        return

    print(f"Chunking corpus from {args.corpus}...")
    chunks = chunk_corpus(args.corpus, size=args.size, overlap=args.overlap)
    print(f"  {len(chunks)} chunks.")

    dim = EMBEDDING_DIMS[args.model]
    print(f"Migrating cache → Qdrant collection {args.collection!r} (dim={dim})...")
    store = migrate_from_json_cache(
        json_path=str(cache_path),
        chunks=chunks,
        embedding_model=args.model,
        dim=dim,
        collection_name=args.collection,
    )

    count = collection_count(store)
    print(f"  Done. Collection has {count} points.")
    print()
    print("Next: try a sample query.")
    print("  python -c \"")
    print("    from src import _bootstrap")
    print("    from src.rag.qdrant_store import load_store")
    print("    from src.rag.qdrant_rag import ask_rag")
    print(f"    store = load_store(collection_name={args.collection!r}, "
          f"embedding_model={args.model!r}, dim={dim})")
    print("    r = ask_rag('What is our leave policy?', store)")
    print("    print(r['answer'])")
    print("  \"")


if __name__ == "__main__":
    main()
