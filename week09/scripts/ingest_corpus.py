"""Run the full W8 ingestion pipeline on a corpus directory.

This is the W8 Lab Step 1 script. End-to-end:
  parse → chunk → metadata → PII → embed → upsert to Qdrant.

Usage:
    # With regex-only PII (default)
    python scripts/ingest_corpus.py

    # With Presidio PII (the Lab Step 1 upgrade)
    python scripts/ingest_corpus.py --use-presidio

    # Different collection
    python scripts/ingest_corpus.py --collection my_chunks_v2

    # Different embedding model
    python scripts/ingest_corpus.py --model text-embedding-3-large
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import _bootstrap  # noqa: F401

import argparse

from src.ingest.pipeline import COLLECTION_NAME_V2, ingest_corpus
from src.rag.embeddings import EMBEDDING_RATES


def main() -> None:
    parser = argparse.ArgumentParser(description="W8 ingestion pipeline.")
    parser.add_argument("--corpus", default="data/corpus",
                        help="Directory of source documents")
    parser.add_argument("--collection", default=COLLECTION_NAME_V2,
                        help="Qdrant collection name (default: capstone_chunks_v2)")
    parser.add_argument("--model", default="text-embedding-3-small",
                        choices=list(EMBEDDING_RATES.keys()),
                        help="OpenAI embedding model")
    parser.add_argument("--use-presidio", action="store_true",
                        help="Enable Presidio NER for names + addresses + orgs")
    parser.add_argument("--target-size", type=int, default=500,
                        help="Target chunk size (chars)")
    parser.add_argument("--max-size", type=int, default=800,
                        help="Hard ceiling for chunk size")
    args = parser.parse_args()

    print(f"=== W8 Ingestion ===")
    print(f"Corpus: {args.corpus}")
    print(f"Collection: {args.collection}")
    print(f"Embedding: {args.model}")
    print(f"PII strategy: {'regex + Presidio' if args.use_presidio else 'regex only'}")
    print()

    result = ingest_corpus(
        corpus_dir=args.corpus,
        embedding_model=args.model,
        collection_name=args.collection,
        use_presidio=args.use_presidio,
        target_chunk_size=args.target_size,
        max_chunk_size=args.max_size,
    )

    print()
    print(f"=== Done ===")
    print(f"  Documents processed: {result.n_documents_processed}")
    print(f"  Documents skipped:   {result.n_documents_skipped}")
    if result.skipped_paths:
        for p in result.skipped_paths:
            print(f"    - {p}")
    print(f"  Chunks produced:     {result.n_chunks}")
    print(f"  Chunks with PII:     {result.n_chunks_with_pii}")
    print(f"  PII types found:     {result.pii_types_found}")
    print()
    print(f"  By doc_type: {result.summary.get('doc_types', {})}")
    print()
    print(f"Next: python scripts/audit_pii.py --collection {args.collection}")


if __name__ == "__main__":
    main()
