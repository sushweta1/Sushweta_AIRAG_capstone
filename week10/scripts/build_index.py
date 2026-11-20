"""Build the JSON embedding cache from the corpus.

This is W6's `build_index.py` extended with a `--model` flag so
learners can pre-populate the cache for either embedding model.

Usage:
    python scripts/build_index.py                                # default: text-embedding-3-small
    python scripts/build_index.py --model text-embedding-3-large
"""
import sys
from pathlib import Path

# Bootstrap sys.path so `from src...` resolves
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Run env bootstrap before any numpy import
from src import _bootstrap  # noqa: F401

import argparse

from src.rag.chunker import chunk_corpus
from src.rag.embeddings import EMBEDDING_RATES, embed, estimate_embedding_cost


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the JSON embedding cache.")
    parser.add_argument("--corpus", default="data/corpus",
                        help="Directory of .md documents to chunk")
    parser.add_argument("--out", default="data/embeddings.json",
                        help="Path to write the JSON cache")
    parser.add_argument("--model", default="text-embedding-3-small",
                        choices=list(EMBEDDING_RATES.keys()),
                        help="Embedding model to use")
    parser.add_argument("--size", type=int, default=500,
                        help="Chunk size (chars)")
    parser.add_argument("--overlap", type=int, default=50,
                        help="Chunk overlap (chars)")
    args = parser.parse_args()

    print(f"Chunking corpus from {args.corpus} (size={args.size}, overlap={args.overlap})...")
    chunks = chunk_corpus(args.corpus, size=args.size, overlap=args.overlap)
    print(f"  {len(chunks)} chunks produced.")

    print(f"Embedding with model={args.model}...")
    texts = [c.text for c in chunks]
    # The embed() function writes to data/embeddings.json by default; pass --out
    vectors = embed(texts, model=args.model, cache_path=args.out)
    dim = len(vectors[0]) if vectors else 0

    # Rough cost estimate (assume ~4 chars per token)
    approx_tokens = sum(len(t) for t in texts) // 4
    est_cost = estimate_embedding_cost(approx_tokens, args.model)
    print(f"  {len(vectors)} chunks embedded; dim = {dim}; ~${est_cost:.5f} estimated")
    print(f"  Cache written to {args.out}.")


if __name__ == "__main__":
    main()
