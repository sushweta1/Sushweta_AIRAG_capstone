"""Compare dense vs hybrid vs hybrid+rerank on the full golden set.

This is the W9 Lab Step 1 script. Runs all 20 golden questions through
each of the 3 retrieval methods, writes per-question results +
aggregate numbers to docs/wk9-retrieval-comparison.md.

Usage:
    python scripts/compare_retrieval_methods.py
    python scripts/compare_retrieval_methods.py --k 5     # top-5 instead of top-3
    python scripts/compare_retrieval_methods.py --methods dense,hybrid
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import _bootstrap  # noqa: F401

import argparse
import json
import time

from src.rag.embeddings import EMBEDDING_DIMS
from src.rag.qdrant_rag import ask_rag, VALID_METHODS
from src.rag.qdrant_store import COLLECTION_NAME_V2, load_store
from src.rag.retrieval import build_bm25_index, load_chunks_from_qdrant


def load_golden(path: str) -> list[dict]:
    p = Path(path)
    return [json.loads(line) for line in p.read_text().splitlines() if line.strip()]


def run_method(method: str, store, chunks, bm25_index,
                golden: list[dict], k: int) -> dict:
    """Run all golden questions with one retrieval method. Return stats."""
    rows = []
    hits = 0
    total_cost = 0.0
    latencies = []
    retrieve_latencies = []

    for entry in golden:
        try:
            kwargs = {"k": k, "retrieval_method": method}
            if method != "dense":
                kwargs["bm25_index"] = bm25_index
                kwargs["chunks"] = chunks

            result = ask_rag(entry["question"], store, **kwargs)
            hit = entry.get("expected_source", "") in result["sources"]
            if hit:
                hits += 1
            total_cost += result["cost_usd"]
            latencies.append(result["latency_ms"])
            retrieve_latencies.append(result.get("retrieve_ms", 0))
            rows.append({
                "id": entry["id"],
                "question": entry["question"][:60],
                "expected": entry.get("expected_source", ""),
                "got": result["sources"][0] if result["sources"] else "(none)",
                "hit": hit,
                "score": (result["citations"][0]["score"]
                          if result.get("citations") else 0),
                "retrieve_ms": result.get("retrieve_ms", 0),
            })
        except Exception as e:
            rows.append({"id": entry["id"], "error": str(e)[:100], "hit": False})
        # gentle pacing to avoid rate limits
        time.sleep(0.15)

    latencies.sort()
    retrieve_latencies.sort()
    return {
        "method": method,
        "hits": hits,
        "total": len(golden),
        "cost_total": total_cost,
        "p50_total": latencies[len(latencies) // 2] if latencies else 0,
        "p95_total": latencies[int(len(latencies) * 0.95) - 1] if latencies else 0,
        "p50_retrieve": (retrieve_latencies[len(retrieve_latencies) // 2]
                         if retrieve_latencies else 0),
        "rows": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--golden", default="data/golden_set_full.jsonl")
    parser.add_argument("--collection", default=COLLECTION_NAME_V2)
    parser.add_argument("--model", default="text-embedding-3-small")
    parser.add_argument("--k", type=int, default=3)
    parser.add_argument("--methods", default="dense,hybrid,hybrid_rerank",
                        help="Comma-separated list of methods to compare")
    parser.add_argument("--output", default="docs/wk9-retrieval-comparison.md")
    args = parser.parse_args()

    methods = [m.strip() for m in args.methods.split(",")]
    for m in methods:
        if m not in VALID_METHODS:
            raise SystemExit(f"Unknown method {m!r}; valid: {VALID_METHODS}")

    print(f"Loading golden set from {args.golden}...")
    golden = load_golden(args.golden)
    print(f"  {len(golden)} questions.")

    print(f"\nLoading store ({args.collection})...")
    dim = EMBEDDING_DIMS[args.model]
    store = load_store(collection_name=args.collection,
                       embedding_model=args.model, dim=dim)

    print(f"\nPulling all chunks for BM25 index...")
    chunks = load_chunks_from_qdrant(store)
    print(f"  Loaded {len(chunks)} chunks.")

    print(f"\nBuilding BM25 index...")
    bm25_index = build_bm25_index(chunks)
    print(f"  BM25 index ready.")

    results = {}
    for method in methods:
        print(f"\n=== Running method: {method} ===")
        r = run_method(method, store, chunks, bm25_index, golden, args.k)
        results[method] = r
        pct = 100 * r["hits"] / r["total"] if r["total"] else 0
        print(f"  Hits: {r['hits']}/{r['total']} ({pct:.0f}%)")
        print(f"  Cost: ${r['cost_total']:.5f}")
        print(f"  Latency p50 (retrieve only): {r['p50_retrieve']}ms")
        print(f"  Latency p50/p95 (end-to-end): {r['p50_total']}ms / {r['p95_total']}ms")

    # Write comparison doc
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w") as f:
        f.write(f"# W9 Retrieval Method Comparison\n\n")
        f.write(f"Compared {len(methods)} retrieval methods on the "
                f"{len(golden)}-question golden set, k={args.k}.\n\n")

        f.write("## Summary\n\n")
        f.write("| Method | Hits | Hit rate | Cost | Retrieve p50 | E2E p50/p95 |\n")
        f.write("|---|---|---|---|---|---|\n")
        for method in methods:
            r = results[method]
            pct = 100 * r["hits"] / r["total"] if r["total"] else 0
            f.write(
                f"| {method} | {r['hits']}/{r['total']} | {pct:.0f}% | "
                f"${r['cost_total']:.5f} | {r['p50_retrieve']}ms | "
                f"{r['p50_total']}ms / {r['p95_total']}ms |\n"
            )

        f.write("\n## Per-question results\n\n")
        f.write("| Q | Question | Expected source | " +
                " | ".join(methods) + " |\n")
        f.write("|---|---|---|" + "---|" * len(methods) + "\n")
        by_q = {entry["id"]: entry for entry in golden}
        for qid, entry in by_q.items():
            row = f"| {qid} | {entry['question'][:55]} | {entry.get('expected_source', '')} |"
            for method in methods:
                m_rows = {r["id"]: r for r in results[method]["rows"]}
                m_row = m_rows.get(qid, {})
                if m_row.get("error"):
                    row += " err |"
                elif m_row.get("hit"):
                    row += " ✓ |"
                else:
                    row += " ✗ |"
            f.write(row + "\n")

    print(f"\nWrote comparison to {out}")


if __name__ == "__main__":
    main()
