"""Try one query rewriting technique on the golden set.

This is the W9 Lab Step 4 (Stretch) script. Pick ONE technique (HyDE,
multi-query, or step-back), apply it to all 20 questions, retrieve
with the rewritten query, measure precision@k.

Usage:
    python scripts/try_query_rewrite.py --technique hyde
    python scripts/try_query_rewrite.py --technique multi_query
    python scripts/try_query_rewrite.py --technique step_back
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import _bootstrap  # noqa: F401

import argparse
import json
import time

from src.rag.embeddings import EMBEDDING_DIMS
from src.rag.qdrant_store import COLLECTION_NAME_V2, load_store
from src.rag.retrieval import (
    build_bm25_index, hybrid_rerank_retrieve, load_chunks_from_qdrant,
)
from src.rag.query_rewrite import (
    hyde_rewrite, multi_query_rewrite, step_back_rewrite,
)


TECHNIQUES = ("hyde", "multi_query", "step_back")


def load_golden(path: str) -> list[dict]:
    p = Path(path)
    return [json.loads(line) for line in p.read_text().splitlines() if line.strip()]


def precision_at_k(retrieved: list[dict], expected_source: str, k: int) -> float:
    if k <= 0 or not retrieved:
        return 0.0
    top_k = retrieved[:k]
    relevant = sum(1 for r in top_k if r.get("source") == expected_source)
    return relevant / k


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--technique", required=True, choices=TECHNIQUES)
    parser.add_argument("--golden", default="data/golden_set_full.jsonl")
    parser.add_argument("--collection", default=COLLECTION_NAME_V2)
    parser.add_argument("--model", default="text-embedding-3-small")
    parser.add_argument("--output", default="docs/wk9-query-rewrite-trial.md")
    args = parser.parse_args()

    print(f"Loading golden set...")
    golden = load_golden(args.golden)
    print(f"  {len(golden)} questions.")

    print(f"Loading store...")
    dim = EMBEDDING_DIMS[args.model]
    store = load_store(collection_name=args.collection,
                       embedding_model=args.model, dim=dim)
    chunks = load_chunks_from_qdrant(store)
    bm25_index = build_bm25_index(chunks)
    print(f"  {len(chunks)} chunks; BM25 built.")

    print(f"\n=== Technique: {args.technique} ===\n")

    p3_baseline_sum = 0.0
    p3_rewrite_sum = 0.0
    per_q = []

    for entry in golden:
        question = entry["question"]
        expected = entry.get("expected_source", "")

        # Baseline: hybrid+rerank on the original question
        baseline = hybrid_rerank_retrieve(
            store=store, bm25_index=bm25_index, chunks=chunks,
            query=question, k_candidates=20, top_k=5,
        )
        p3_baseline = precision_at_k(baseline, expected, 3)
        p3_baseline_sum += p3_baseline

        # Rewrite + retrieve
        if args.technique == "hyde":
            rewritten = hyde_rewrite(question)
            retrieved = hybrid_rerank_retrieve(
                store=store, bm25_index=bm25_index, chunks=chunks,
                query=rewritten, k_candidates=20, top_k=5,
            )
            rewrite_display = rewritten[:80] + "..."
        elif args.technique == "step_back":
            stepback = step_back_rewrite(question)
            # Run both original AND step-back; merge (dedup by source/text)
            r1 = hybrid_rerank_retrieve(
                store=store, bm25_index=bm25_index, chunks=chunks,
                query=question, k_candidates=20, top_k=5,
            )
            r2 = hybrid_rerank_retrieve(
                store=store, bm25_index=bm25_index, chunks=chunks,
                query=stepback, k_candidates=20, top_k=5,
            )
            seen = set()
            retrieved = []
            for r in r1 + r2:
                key = (r.get("source", ""), r.get("text", "")[:100])
                if key in seen:
                    continue
                seen.add(key)
                retrieved.append(r)
            rewrite_display = stepback[:80]
        else:  # multi_query
            paraphrases = multi_query_rewrite(question, n=3)
            queries = [question] + paraphrases
            seen = set()
            retrieved = []
            for q in queries:
                hits = hybrid_rerank_retrieve(
                    store=store, bm25_index=bm25_index, chunks=chunks,
                    query=q, k_candidates=20, top_k=5,
                )
                for r in hits:
                    key = (r.get("source", ""), r.get("text", "")[:100])
                    if key in seen:
                        continue
                    seen.add(key)
                    retrieved.append(r)
            rewrite_display = " | ".join(p[:30] for p in paraphrases)

        p3_rewrite = precision_at_k(retrieved, expected, 3)
        p3_rewrite_sum += p3_rewrite

        delta = p3_rewrite - p3_baseline
        marker = "↑" if delta > 0 else ("↓" if delta < 0 else "=")
        print(f"  Q{entry['id']}: baseline={p3_baseline:.2f} "
              f"rewrite={p3_rewrite:.2f} {marker}")

        per_q.append({
            "id": entry["id"],
            "question": question,
            "rewrite": rewrite_display,
            "p3_baseline": p3_baseline,
            "p3_rewrite": p3_rewrite,
            "delta": delta,
        })
        time.sleep(0.1)

    n = len(golden)
    avg_baseline = p3_baseline_sum / n
    avg_rewrite = p3_rewrite_sum / n
    delta_avg = avg_rewrite - avg_baseline

    print(f"\n=== Summary ===")
    print(f"Baseline P@3 (hybrid+rerank only):     {avg_baseline:.3f}")
    print(f"Rewrite P@3 ({args.technique}):  {avg_rewrite:.3f}")
    print(f"Delta:                                 {'+' if delta_avg >= 0 else ''}{delta_avg:.3f}")

    # Verdict
    if delta_avg > 0.05:
        verdict = "**KEEP** — material lift in precision@3"
    elif delta_avg > 0:
        verdict = "Marginal — keep if cost permits"
    elif delta_avg == 0:
        verdict = "No effect — drop (cost without benefit)"
    else:
        verdict = "**DROP** — hurts precision@3"

    print(f"Verdict: {verdict}\n")

    # Write doc
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w") as f:
        f.write(f"# W9 Query Rewriting Trial — {args.technique}\n\n")
        f.write(f"Golden set: {n} questions. Baseline: hybrid+rerank on original question. "
                f"Rewrite: {args.technique} applied.\n\n")
        f.write(f"## Aggregate\n\n")
        f.write(f"| Metric | Value |\n|---|---|\n")
        f.write(f"| Baseline P@3 | {avg_baseline:.3f} |\n")
        f.write(f"| {args.technique} P@3 | {avg_rewrite:.3f} |\n")
        f.write(f"| Delta | {'+' if delta_avg >= 0 else ''}{delta_avg:.3f} |\n")
        f.write(f"| Verdict | {verdict} |\n\n")
        f.write(f"## Per-question\n\n")
        f.write(f"| Q | Question | P@3 base | P@3 rewrite | Δ |\n")
        f.write(f"|---|---|---|---|---|\n")
        for r in per_q:
            sign = "+" if r["delta"] >= 0 else ""
            f.write(f"| {r['id']} | {r['question'][:55]} | "
                    f"{r['p3_baseline']:.2f} | {r['p3_rewrite']:.2f} | "
                    f"{sign}{r['delta']:.2f} |\n")

    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
