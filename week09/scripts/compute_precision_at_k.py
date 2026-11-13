"""Compute precision@k for each retrieval method.

This is the W9 Lab Step 2 script. Precision@k = (number of relevant
chunks in top k) / k. We treat a chunk as relevant if it comes from
the expected_source for that question. Stricter definitions (relevant
chunk = the SPECIFIC passage that answers the question) require a
human-labelled golden set; this approximation is good enough for the
weekly snapshot.

Usage:
    python scripts/compute_precision_at_k.py
    python scripts/compute_precision_at_k.py --methods dense,hybrid_rerank
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import _bootstrap  # noqa: F401

import argparse
import json
import time

from src.rag.embeddings import EMBEDDING_DIMS, embed
from src.rag.qdrant_store import COLLECTION_NAME_V2, load_store, retrieve as qdrant_retrieve
from src.rag.retrieval import (
    build_bm25_index, hybrid_retrieve, hybrid_rerank_retrieve,
    load_chunks_from_qdrant,
)


def load_golden(path: str) -> list[dict]:
    p = Path(path)
    return [json.loads(line) for line in p.read_text().splitlines() if line.strip()]


def precision_at_k(retrieved: list[dict], expected_source: str, k: int) -> float:
    """Fraction of top-k results coming from expected_source."""
    if k <= 0 or not retrieved:
        return 0.0
    top_k = retrieved[:k]
    relevant = sum(1 for r in top_k if r.get("source") == expected_source)
    return relevant / k


def retrieve_for(method: str, store, chunks, bm25_index, question: str,
                  k_max: int = 10) -> list[dict]:
    """Retrieve top-k_max chunks with one method (no LLM call)."""
    if method == "dense":
        query_embedding = embed([question], model=store.embedding_model)[0]
        return qdrant_retrieve(store, query_embedding, k=k_max)
    if method == "hybrid":
        return hybrid_retrieve(
            store=store, bm25_index=bm25_index, chunks=chunks,
            query=question, k_each=k_max, k_final=k_max,
        )
    if method == "hybrid_rerank":
        return hybrid_rerank_retrieve(
            store=store, bm25_index=bm25_index, chunks=chunks,
            query=question, k_candidates=20, top_k=k_max,
        )
    raise ValueError(f"unknown method: {method}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--golden", default="data/golden_set_full.jsonl")
    parser.add_argument("--collection", default=COLLECTION_NAME_V2)
    parser.add_argument("--model", default="text-embedding-3-small")
    parser.add_argument("--methods", default="dense,hybrid,hybrid_rerank")
    parser.add_argument("--output", default="docs/wk9-precision-delta.md")
    args = parser.parse_args()

    methods = [m.strip() for m in args.methods.split(",")]

    print(f"Loading golden set from {args.golden}...")
    golden = load_golden(args.golden)
    print(f"  {len(golden)} questions.")

    print(f"Loading store ({args.collection})...")
    dim = EMBEDDING_DIMS[args.model]
    store = load_store(collection_name=args.collection,
                       embedding_model=args.model, dim=dim)

    print(f"Pulling chunks for BM25 index...")
    chunks = load_chunks_from_qdrant(store)
    bm25_index = build_bm25_index(chunks)
    print(f"  {len(chunks)} chunks; BM25 built.")

    # Run each method, collect precision@3 and precision@5
    results = {}
    for method in methods:
        print(f"\n=== {method} ===")
        p3_sum = 0.0
        p5_sum = 0.0
        per_q = []
        retrieve_ms_list = []

        for entry in golden:
            t0 = time.time()
            retrieved = retrieve_for(method, store, chunks, bm25_index,
                                     entry["question"], k_max=10)
            retrieve_ms = int((time.time() - t0) * 1000)
            retrieve_ms_list.append(retrieve_ms)

            expected = entry.get("expected_source", "")
            p3 = precision_at_k(retrieved, expected, 3)
            p5 = precision_at_k(retrieved, expected, 5)
            p3_sum += p3
            p5_sum += p5

            per_q.append({
                "id": entry["id"],
                "question": entry["question"][:60],
                "expected": expected,
                "p3": p3,
                "p5": p5,
            })
            time.sleep(0.1)

        n = len(golden)
        p3_avg = p3_sum / n if n else 0
        p5_avg = p5_sum / n if n else 0
        retrieve_ms_list.sort()
        results[method] = {
            "p3_avg": p3_avg,
            "p5_avg": p5_avg,
            "per_q": per_q,
            "p50_ms": (retrieve_ms_list[len(retrieve_ms_list) // 2]
                      if retrieve_ms_list else 0),
            "p95_ms": (retrieve_ms_list[int(len(retrieve_ms_list) * 0.95) - 1]
                      if retrieve_ms_list else 0),
        }
        print(f"  precision@3 (avg): {p3_avg:.3f}")
        print(f"  precision@5 (avg): {p5_avg:.3f}")
        print(f"  retrieve p50/p95: {results[method]['p50_ms']}/{results[method]['p95_ms']}ms")

    # Compute deltas vs dense baseline (if dense was run)
    baseline = "dense" if "dense" in methods else methods[0]

    # Write the doc
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w") as f:
        f.write("# W9 Precision@k Delta\n\n")
        f.write(f"Golden set: {len(golden)} questions. ")
        f.write(f"Methods: {', '.join(methods)}. ")
        f.write(f"Baseline for delta: `{baseline}`.\n\n")

        f.write("## Aggregate\n\n")
        f.write("| Method | P@3 | Δ P@3 | P@5 | Δ P@5 | Retrieve p50 | Retrieve p95 |\n")
        f.write("|---|---|---|---|---|---|---|\n")
        b_p3 = results[baseline]["p3_avg"]
        b_p5 = results[baseline]["p5_avg"]
        for method in methods:
            r = results[method]
            dp3 = r["p3_avg"] - b_p3
            dp5 = r["p5_avg"] - b_p5
            f.write(
                f"| {method} | {r['p3_avg']:.3f} | "
                f"{'+' if dp3 >= 0 else ''}{dp3:.3f} | "
                f"{r['p5_avg']:.3f} | "
                f"{'+' if dp5 >= 0 else ''}{dp5:.3f} | "
                f"{r['p50_ms']}ms | {r['p95_ms']}ms |\n"
            )

        f.write("\n## Per-question precision@3\n\n")
        f.write("| Q | Question | Expected | " +
                " | ".join(f"P@3 {m}" for m in methods) + " |\n")
        f.write("|---|---|---|" + "---|" * len(methods) + "\n")
        by_q = {entry["id"]: entry for entry in golden}
        for qid, entry in by_q.items():
            row = f"| {qid} | {entry['question'][:50]} | {entry.get('expected_source', '')[:25]} |"
            for method in methods:
                m_rows = {r["id"]: r for r in results[method]["per_q"]}
                p3 = m_rows.get(qid, {}).get("p3", 0)
                row += f" {p3:.2f} |"
            f.write(row + "\n")

        f.write("\n## Headline (for wk9 snapshot)\n\n")
        if "hybrid_rerank" in results:
            r = results["hybrid_rerank"]
            f.write(
                f"- Precision@3 (hybrid+rerank): **{r['p3_avg']:.3f}** "
                f"({'+' if r['p3_avg'] - b_p3 >= 0 else ''}{r['p3_avg'] - b_p3:.3f} vs {baseline})\n"
            )
            f.write(
                f"- Precision@5 (hybrid+rerank): **{r['p5_avg']:.3f}** "
                f"({'+' if r['p5_avg'] - b_p5 >= 0 else ''}{r['p5_avg'] - b_p5:.3f} vs {baseline})\n"
            )
            f.write(f"- Retrieve latency p50: **{r['p50_ms']}ms**, p95: **{r['p95_ms']}ms**\n")

    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
