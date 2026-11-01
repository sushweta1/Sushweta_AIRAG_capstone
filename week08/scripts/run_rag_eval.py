"""Run RAG eval against a Qdrant store.

Same shape as W6's run_rag_eval — but loads from Qdrant instead of
a JSON file. The output JSONL is identical in format so compute_kpis.py
works unchanged.

Usage:
    # After migrate_to_qdrant.py has populated the collection:
    python scripts/run_rag_eval.py --label wk7-baseline

    # Different embedding model (must have a matching collection)
    python scripts/run_rag_eval.py --label wk7-large \
        --collection capstone_chunks_3_large \
        --model text-embedding-3-large
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
from src.rag.qdrant_store import COLLECTION_NAME_V2, load_store


def load_golden(path: str) -> list[dict]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Golden set not found: {path}")
    return [json.loads(line) for line in p.read_text().splitlines() if line.strip()]


def hit_check(retrieved_sources: list[str], expected_source: str) -> bool:
    return expected_source in retrieved_sources


def main() -> None:
    parser = argparse.ArgumentParser(description="Run RAG eval against Qdrant.")
    parser.add_argument("--collection", default=COLLECTION_NAME_V2)
    parser.add_argument("--model", default="text-embedding-3-small")
    parser.add_argument("--golden", default="data/golden_set_full.jsonl")
    parser.add_argument("--label", required=True)
    parser.add_argument("--k", type=int, default=3)
    parser.add_argument("--output-dir", default="docs/experiments")
    args = parser.parse_args()

    dim = EMBEDDING_DIMS[args.model]
    print(f"Loading Qdrant collection {args.collection!r} (model={args.model}, dim={dim})...")
    store = load_store(collection_name=args.collection,
                        embedding_model=args.model, dim=dim)

    print(f"Loading golden set from {args.golden}...")
    golden = load_golden(args.golden)
    print(f"  {len(golden)} questions.")

    output_path = Path(args.output_dir) / f"run_{args.label}.jsonl"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"\nRunning eval...\n")
    results = []
    hits = 0
    for entry in golden:
        print(f"  [{entry['id']}] {entry['question'][:60]}")
        try:
            result = ask_rag(entry["question"], store, k=args.k)
        except Exception as exc:
            print(f"     ERROR: {exc}")
            result = {
                "answer": None,
                "error": str(exc),
                "sources": [],
                "cost_usd": 0.0,
                "latency_ms": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "chat_model": "gpt-4o-mini",
                "embedding_model": args.model,
            }

        result["id"] = entry["id"]
        result["question"] = entry["question"]
        result["ideal_answer"] = entry.get("ideal_answer", "")
        result["expected_source"] = entry.get("expected_source", "")
        result["hit"] = hit_check(result["sources"], entry.get("expected_source", ""))
        if result["hit"]:
            hits += 1
        results.append(result)
        time.sleep(0.2)

    with output_path.open("w") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")

    print(f"\nWrote {len(results)} rows to {output_path}")
    print(f"\n=== Summary ({args.label}) ===")
    print(f"  Hit rate: {hits} / {len(results)} ({100*hits/len(results):.0f}%)")

    successful = [r for r in results if r.get("error") is None]
    if successful:
        total_cost = sum(r["cost_usd"] for r in successful)
        latencies = sorted(r["latency_ms"] for r in successful)
        p50 = latencies[len(latencies) // 2]
        p95 = latencies[max(0, int(len(latencies) * 0.95) - 1)]
        print(f"  Total chat cost: ${total_cost:.5f}")
        print(f"  Latency p50/p95: {p50}ms / {p95}ms")


if __name__ == "__main__":
    main()
