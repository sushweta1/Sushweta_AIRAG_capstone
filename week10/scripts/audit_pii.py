"""Audit PII scrubbing — sample 10 random chunks from a Qdrant collection.

This is the W8 Lab Step 2 script. The point: trust but verify.
Even with Presidio + regex, PII can leak. The only reliable way to
catch the gaps is to look at random samples.

Usage:
    python scripts/audit_pii.py
    python scripts/audit_pii.py --n 20 --collection capstone_chunks_v2
    python scripts/audit_pii.py --only-pii   # show only chunks where has_pii=True
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import _bootstrap  # noqa: F401

import argparse
import random
import re

from src.ingest.pipeline import COLLECTION_NAME_V2
from src.rag.qdrant_store import _get_client


# Quick regex check — does any chunk text STILL contain PII patterns?
PII_RE = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b|"     # email
    r"\b(?:\+?\d{1,3}[\s-]?)?(?:\(\d{2,4}\)|\d{2,4})[\s-]?\d{3,4}[\s-]?\d{3,4}\b|"  # phone
    r"\b\d{3}-\d{2}-\d{4}\b"                                    # SSN
)


def fetch_random_points(client, collection: str, n: int = 10) -> list:
    """Get N random points from a Qdrant collection."""
    info = client.get_collection(collection)
    total = info.points_count
    if total == 0:
        return []

    # Use scroll to get a batch, then sample. For small collections (< 1000),
    # this gets effectively-random points.
    response = client.scroll(
        collection_name=collection,
        limit=min(total, 200),
        with_payload=True,
        with_vectors=False,
    )
    points = response[0]
    if len(points) <= n:
        return points
    return random.sample(points, n)


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit PII in a Qdrant collection.")
    parser.add_argument("--collection", default=COLLECTION_NAME_V2)
    parser.add_argument("--n", type=int, default=10,
                        help="Number of chunks to sample")
    parser.add_argument("--only-pii", action="store_true",
                        help="Show only chunks where has_pii=True")
    args = parser.parse_args()

    client = _get_client()

    print(f"=== PII Audit ===")
    print(f"Collection: {args.collection}")

    try:
        info = client.get_collection(args.collection)
    except Exception as e:
        print(f"ERROR: collection {args.collection!r} not found ({e})")
        print(f"Run scripts/ingest_corpus.py first.")
        return

    total = info.points_count
    print(f"Total points in collection: {total}")
    print(f"Sampling {args.n} random chunks...")
    print()

    points = fetch_random_points(client, args.collection, n=args.n)
    if args.only_pii:
        points = [p for p in points if (p.payload or {}).get("has_pii")]
        print(f"Filtered to has_pii=True: {len(points)} chunks")
        print()

    found_residual = 0
    for i, point in enumerate(points, 1):
        payload = point.payload or {}
        text = payload.get("text", "")
        source = payload.get("source", "unknown")
        section_path = payload.get("section_path", "")
        has_pii_flag = payload.get("has_pii", False)
        pii_types = payload.get("pii_types", [])

        # Check for residual PII patterns (things we should have scrubbed)
        residuals = PII_RE.findall(text)

        # Status indicator
        if residuals:
            status = "⚠  POSSIBLE RESIDUAL PII"
            found_residual += 1
        elif has_pii_flag:
            status = "✓  scrubbed"
        else:
            status = "·  clean"

        print(f"[{i:02d}/{len(points)}] {status}")
        print(f"     source: {source}")
        if section_path:
            print(f"     section: {section_path}")
        if has_pii_flag:
            print(f"     scrubbed types: {pii_types}")
        if residuals:
            print(f"     RESIDUAL MATCHES: {residuals}")
        print(f"     text[:200]: {text[:200]!r}")
        print()

    print(f"=== Summary ===")
    print(f"  Sampled: {len(points)} chunks")
    print(f"  Possible residual PII: {found_residual}")
    if found_residual > 0:
        print(f"")
        print(f"  ⚠  Investigate the chunks flagged above. The scrubber may have")
        print(f"     missed something. Consider re-running with --use-presidio,")
        print(f"     or extending the regex in src/ingest/pii.py.")
    else:
        print(f"")
        print(f"  ✓  No residual PII detected in this sample. Run again with")
        print(f"     a larger --n for stronger confidence.")


if __name__ == "__main__":
    main()
