"""Compare W7 (capstone_chunks) vs W8 (capstone_chunks_v2) on the golden set.

This is a Lab Step 3 helper. Runs all 20 golden questions through
both collections, computes hit rate + cost + latency, writes a
side-by-side comparison to docs/experiments/wk8-v1-vs-v2.md.

Requires both collections to exist:
  - capstone_chunks      (from W7's migrate_to_qdrant.py)
  - capstone_chunks_v2   (from W8's scripts/ingest_corpus.py)

Usage:
    python scripts/compare_v1_vs_v2.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import _bootstrap  # noqa: F401

import argparse
import json
import time

from src.rag.embeddings import EMBEDDING_DIMS
from src.rag.qdrant_rag import ask_rag
from src.rag.qdrant_store import _get_client, load_store


def load_golden(path: str) -> list[dict]:
    p = Path(path)
    return [json.loads(line) for line in p.read_text().splitlines() if line.strip()]


def run_against(collection: str, model: str, golden: list[dict], k: int) -> dict:
    """Run all golden questions against one collection. Returns stats + per-q rows."""
    dim = EMBEDDING_DIMS[model]
    store = load_store(collection_name=collection, embedding_model=model, dim=dim)

    rows = []
    hits = 0
    total_cost = 0.0
    latencies = []
    for entry in golden:
        try:
            result = ask_rag(entry["question"], store, k=k)
            hit = entry.get("expected_source", "") in result["sources"]
            if hit:
                hits += 1
            total_cost += result["cost_usd"]
            latencies.append(result["latency_ms"])
            rows.append({
                "id": entry["id"],
                "question": entry["question"][:60],
                "expected": entry.get("expected_source", ""),
                "got": result["sources"][0] if result["sources"] else "(none)",
                "section": (result["citations"][0].get("section_path", "")
                            if result.get("citations") else ""),
                "hit": hit,
            })
        except Exception as e:
            rows.append({"id": entry["id"], "error": str(e), "hit": False})
        time.sleep(0.15)

    latencies.sort()
    return {
        "hits": hits,
        "total": len(golden),
        "cost_total": total_cost,
        "p50": latencies[len(latencies) // 2] if latencies else 0,
        "p95": latencies[int(len(latencies) * 0.95) - 1] if latencies else 0,
        "rows": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--golden", default="data/golden_set_full.jsonl")
    parser.add_argument("--model", default="text-embedding-3-small")
    parser.add_argument("--v1", default="capstone_chunks", help="W7 collection")
    parser.add_argument("--v2", default="capstone_chunks_v2", help="W8 collection")
    parser.add_argument("--k", type=int, default=3)
    parser.add_argument("--output", default="docs/experiments/wk8-v1-vs-v2.md")
    args = parser.parse_args()

    # Validate both collections exist
    client = _get_client()
    existing = {c.name for c in client.get_collections().collections}
    missing = [c for c in [args.v1, args.v2] if c not in existing]
    if missing:
        print(f"ERROR: missing collections: {missing}")
        print(f"Available: {sorted(existing)}")
        return

    print(f"Loading golden set from {args.golden}...")
    golden = load_golden(args.golden)
    print(f"  {len(golden)} questions.")

    print(f"\n=== Running against {args.v1} (W7 baseline, no metadata) ===")
    v1 = run_against(args.v1, args.model, golden, args.k)
    print(f"  Hits: {v1['hits']}/{v1['total']} ({100 * v1['hits'] / v1['total']:.0f}%)")
    print(f"  Cost: ${v1['cost_total']:.5f}")
    print(f"  Latency p50/p95: {v1['p50']}ms / {v1['p95']}ms")

    print(f"\n=== Running against {args.v2} (W8 enriched, with metadata) ===")
    v2 = run_against(args.v2, args.model, golden, args.k)
    print(f"  Hits: {v2['hits']}/{v2['total']} ({100 * v2['hits'] / v2['total']:.0f}%)")
    print(f"  Cost: ${v2['cost_total']:.5f}")
    print(f"  Latency p50/p95: {v2['p50']}ms / {v2['p95']}ms")

    # Write comparison doc
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w") as f:
        f.write("# W7 vs W8 — Collection Comparison\n\n")
        f.write(f"Ran {len(golden)} golden questions against both collections "
                f"with the same embedding model ({args.model}).\n\n")
        f.write("## Summary\n\n")
        f.write(f"| Metric | W7 {args.v1} | W8 {args.v2} | Δ |\n")
        f.write("|---|---|---|---|\n")
        delta_hits = v2['hits'] - v1['hits']
        f.write(f"| Hit rate | {v1['hits']}/{v1['total']} ({100*v1['hits']/v1['total']:.0f}%) | "
                f"{v2['hits']}/{v2['total']} ({100*v2['hits']/v2['total']:.0f}%) | "
                f"{'+' if delta_hits >= 0 else ''}{delta_hits} |\n")
        f.write(f"| Cost (total) | ${v1['cost_total']:.5f} | ${v2['cost_total']:.5f} | "
                f"${v2['cost_total'] - v1['cost_total']:+.5f} |\n")
        f.write(f"| Latency p50 | {v1['p50']}ms | {v2['p50']}ms | "
                f"{v2['p50'] - v1['p50']:+d}ms |\n")
        f.write(f"| Latency p95 | {v1['p95']}ms | {v2['p95']}ms | "
                f"{v2['p95'] - v1['p95']:+d}ms |\n")

        f.write("\n## Per-question diff\n\n")
        f.write("| Q | Question | W7 got | W8 got | W7 hit | W8 hit |\n")
        f.write("|---|---|---|---|---|---|\n")
        v1_by_id = {r["id"]: r for r in v1["rows"]}
        v2_by_id = {r["id"]: r for r in v2["rows"]}
        for entry in golden:
            qid = entry["id"]
            r1 = v1_by_id.get(qid, {})
            r2 = v2_by_id.get(qid, {})
            f.write(f"| {qid} | {entry['question'][:60]} | "
                    f"{r1.get('got', '?')} | {r2.get('got', '?')} | "
                    f"{'✓' if r1.get('hit') else '✗'} | "
                    f"{'✓' if r2.get('hit') else '✗'} |\n")

    print(f"\nWrote comparison to {out}")


if __name__ == "__main__":
    main()
