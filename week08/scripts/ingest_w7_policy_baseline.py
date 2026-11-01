"""Matched Week 7-style baseline for the Week 8 HR/IT corpus."""

import argparse
from pathlib import Path

from src.ingest.parsers import parse_document
from src.ingest.pii import scrub_pii
from src.ingest.name_redaction import redact_known_names, KNOWN_NAMES
from src.rag.chunker import Chunk, chunk_text

COLLECTION = "capstone_chunks_w7_baseline"
CACHE = "data/embeddings_w7_policy_baseline.json"
MODEL = "text-embedding-3-small"
EXTENSIONS = {".md", ".pdf", ".docx", ".html", ".htm", ".txt"}


def prepare_chunks():
    chunks = []
    documents = 0

    for path in sorted(Path("data/corpus").iterdir()):
        if path.suffix.lower() not in EXTENSIONS:
            continue

        doc = parse_document(path)
        documents += 1

        for chunk in chunk_text(
            doc.raw_text, source=doc.source,
            size=500, overlap=50
        ):
            cleaned = redact_known_names(
                scrub_pii(chunk.text).redacted
            )

            for name in KNOWN_NAMES:
                if name.lower() in cleaned.lower():
                    raise ValueError("Known name remains after redaction")

            if "+971 4 555 9876" in cleaned:
                raise ValueError("Known phone number remains")

            chunks.append(Chunk(text=cleaned, source=doc.source))

    if documents != 7 or len(chunks) != 16:
        raise ValueError(
            f"Unexpected corpus: {documents} documents, "
            f"{len(chunks)} chunks"
        )

    return chunks


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--execute", action="store_true",
        help="Generate embeddings and create Qdrant collection"
    )
    args = parser.parse_args()

    chunks = prepare_chunks()

    print("=== Matched Baseline ===")
    print("Documents: 7")
    print("Chunks:", len(chunks))
    print("Embedding model:", MODEL)
    print("Collection:", COLLECTION)

    if not args.execute:
        print("DRY RUN — no external API calls or Qdrant writes")
        return

    from src.rag.embeddings import embed, EMBEDDING_DIMS
    from src.rag.qdrant_store import _get_client, build_store

    client = _get_client()
    existing = {c.name for c in client.get_collections().collections}

    if COLLECTION in existing:
        raise RuntimeError(
            f"Collection {COLLECTION} already exists. "
            "Refusing to overwrite or append."
        )

    vectors = embed(
        [chunk.text for chunk in chunks],
        model=MODEL,
        cache_path=CACHE,
    )

    build_store(
        chunks,
        vectors,
        embedding_model=MODEL,
        dim=EMBEDDING_DIMS[MODEL],
        collection_name=COLLECTION,
        reset=False,
    )

    print("Baseline collection created:", COLLECTION)


if __name__ == "__main__":
    main()
