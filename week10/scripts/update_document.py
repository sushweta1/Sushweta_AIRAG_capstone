"""Week 10 — Update an existing knowledge base document."""

import argparse
import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from src.ingest.pipeline import update_document
from src.rag.cache import SemanticCache
from src.rag.kb_version import get_kb_version
from src.rag.qdrant_store import (
    COLLECTION_NAME_V10,
    load_store,
)


def main():

    parser = argparse.ArgumentParser(
        description=(
            "Replace an existing document in the "
            "Week 10 knowledge base."
        )
    )

    parser.add_argument(
        "--document",
        required=True,
        help="Path to the replacement document.",
    )

    parser.add_argument(
        "--cache",
        default="data/cache/results.db",
        help="Response cache database.",
    )

    parser.add_argument(
        "--model",
        default="text-embedding-3-small",
        choices=["text-embedding-3-small"],
        help="Embedding model.",
    )

    parser.add_argument(
        "--use-presidio",
        action="store_true",
        help="Enable Presidio PII redaction.",
    )

    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Explicitly authorize document replacement.",
    )

    args = parser.parse_args()

    document = Path(args.document).resolve()

    if not document.is_file():
        parser.error(f"Document not found: {document}")

    print("\n--- Week 10 Document Update ---")
    print("Collection:", COLLECTION_NAME_V10)
    print("Document:", document.name)
    print("Current KB version:", get_kb_version())
    print("Embedding model:", args.model)
    print("Cache:", args.cache)

    if not args.confirm:
        print("\nPREVIEW ONLY: No changes made.")
        print("Add --confirm to execute the update.")
        return 0

    store = load_store(
        collection_name=COLLECTION_NAME_V10,
        embedding_model=args.model,
        dim=1536,
    )

    cache = SemanticCache(args.cache)

    try:

        result = update_document(
            document_path=document,
            store=store,
            cache=cache,
            use_presidio=args.use_presidio,
        )

        print("\n--- Update Result ---")
        print(json.dumps(result, indent=2))

        print("\nSUCCESS: Document replacement completed.")

        return 0

    except Exception as error:

        print(
            f"\nERROR: {error}",
            file=sys.stderr,
        )

        return 1

    finally:

        cache.close()
        store.client.close()


if __name__ == "__main__":
    sys.exit(main())
