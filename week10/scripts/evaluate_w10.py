"""Week 10 cold/warm RAG evaluation.

Runs the 20-question golden set twice:
  cold: populate a fresh response cache
  warm: repeat identical questions

Retrieval hits are not treated as answer correctness.
"""
import argparse
import json
import math
import os
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from src.rag.cache import SemanticCache
from src.rag.kb_version import get_kb_version
from src.rag.qdrant_rag import ask_rag
from src.rag.qdrant_store import load_store, live_filter

COLLECTION = "capstone_chunks_v10"
GOLDEN_PATH = ROOT / "data/golden_set_full.jsonl"
CACHE_PATH = ROOT / "data/cache/wk10_eval.db"
RESULTS_DIR = ROOT / "results/wk10"


def percentile(values, fraction):
    if not values:
        return None
    values = sorted(values)
    index = math.ceil(len(values) * fraction) - 1
    return values[max(0, index)]


def summarize(rows):
    latencies = [r["latency_ms"] for r in rows]
    costs = [r["cost_usd"] for r in rows]
    total = len(rows)

    return {
        "questions": total,
        "retrieval_hit_rate": (
            sum(r["retrieval_hit"] for r in rows) / total
        ),
        "cache_hit_rate": (
            sum(r["cache_hit"] for r in rows) / total
        ),
        "exact_cache_hits": sum(
            r["cache_match"] == "exact" for r in rows
        ),
        "semantic_cache_hits": sum(
            r["cache_match"] == "semantic" for r in rows
        ),
        "latency_p50_ms": percentile(latencies, 0.50),
        "latency_p95_ms": percentile(latencies, 0.95),
        "mean_latency_ms": round(
            statistics.mean(latencies), 2
        ),
        "total_chat_cost_usd": round(sum(costs), 9),
        "mean_chat_cost_usd": round(
            statistics.mean(costs), 9
        ),
    }


def run_pass(name, golden, store, cache, version):
    output = []

    print(f"\n=== {name.upper()} PASS ===", flush=True)

    for i, item in enumerate(golden, 1):
        question = item["question"]

        result = ask_rag(
            question=question,
            store=store,
            cache=cache,
            k=3,
            retrieval_method="dense",
            kb_version=version,
            cache_scope="wk10-golden-eval",
        )

        sources = result.get("sources") or []

        row = {
            "id": item["id"],
            "question": question,
            "ideal_answer": item["ideal_answer"],
            "expected_source": item["expected_source"],
            "tags": item.get("tags", []),
            "answer": result["answer"],
            "sources": sources,
            "citations": result.get("citations", []),
            "retrieved_chunks": result.get(
                "retrieved_chunks", []
            ),
            "retrieval_hit": (
                item["expected_source"] in sources
            ),
            "cache_hit": result["cache_hit"],
            "cache_match": result["cache_match"],
            "cache_similarity": result.get(
                "cache_similarity"
            ),
            "latency_ms": result["latency_ms"],
            "embed_ms": result.get("embed_ms", 0),
            "retrieve_ms": result.get("retrieve_ms", 0),
            "generate_ms": result.get("generate_ms", 0),
            "cost_usd": result.get("cost_usd", 0),
            "prompt_tokens": result.get(
                "prompt_tokens", 0
            ),
            "completion_tokens": result.get(
                "completion_tokens", 0
            ),
            "kb_version": result["kb_version"],
        }

        output.append(row)

        status = "HIT" if row["cache_hit"] else "MISS"
        retrieval = (
            "SOURCE_OK"
            if row["retrieval_hit"]
            else "SOURCE_MISS"
        )

        print(
            f'{i:02d}/{len(golden)} '
            f'{item["id"]} '
            f'{status:<4} '
            f'{retrieval:<11} '
            f'{row["latency_ms"]:>5}ms '
            f'${row["cost_usd"]:.7f}',
            flush=True,
        )

    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Run live OpenAI calls and write evaluation files",
    )
    args = parser.parse_args()

    golden = [
        json.loads(line)
        for line in GOLDEN_PATH.read_text(
            encoding="utf-8"
        ).splitlines()
        if line.strip()
    ]

    ids = [row["id"] for row in golden]
    questions = [row["question"] for row in golden]

    assert len(golden) == 20
    assert len(set(ids)) == 20
    assert len(set(questions)) == 20

    version = get_kb_version()

    print("--- Week 10 Golden-Set Evaluation ---")
    print("Collection:", COLLECTION)
    print("KB version:", version)
    print("Questions:", len(golden))
    print("Cache:", CACHE_PATH)
    print("Results:", RESULTS_DIR)

    if not args.confirm:
        print("\nPREVIEW ONLY. Add --confirm to run.")
        return

    assert version == "v2.w10.2", (
        "KB version changed; review before evaluating."
    )

    store = load_store(collection_name=COLLECTION)
    cache = SemanticCache(str(CACHE_PATH))

    try:
        total = store.client.count(
            collection_name=COLLECTION,
            exact=True,
        ).count

        live = store.client.count(
            collection_name=COLLECTION,
            count_filter=live_filter(),
            exact=True,
        ).count

        assert total == 26, (
            f"Expected 26 stored chunks; got {total}"
        )
        assert live == 24, (
            f"Expected 24 live chunks; got {live}"
        )

        cache.clear()

        cold = run_pass(
            "cold", golden, store, cache, version
        )

        warm = run_pass(
            "warm", golden, store, cache, version
        )

        for before, after in zip(cold, warm):
            assert before["id"] == after["id"]
            assert not before["cache_hit"], (
                f'Unexpected cold hit: {before["id"]}'
            )
            assert after["cache_hit"], (
                f'Missing warm hit: {after["id"]}'
            )
            assert after["cache_match"] == "exact"
            assert before["answer"] == after["answer"]
            assert before["citations"] == after["citations"]

        cold_summary = summarize(cold)
        warm_summary = summarize(warm)

        consistency = sum(
            a["answer"] == b["answer"]
            for a, b in zip(cold, warm)
        ) / len(cold)

        summary = {
            "created_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "collection": COLLECTION,
            "kb_version": version,
            "retrieval_method": "dense",
            "k": 3,
            "golden_questions": len(golden),
            "cold": cold_summary,
            "warm": warm_summary,
            "answer_consistency_rate": consistency,
            "task_success_rate": None,
            "task_success_note": (
                "Not scored: requires independent "
                "answer correctness evaluation."
            ),
            "embedding_cost_note": (
                "Not included in chat cost. Embedding "
                "usage must be measured or estimated "
                "separately."
            ),
        }

        RESULTS_DIR.mkdir(
            parents=True, exist_ok=True
        )

        for name, rows in [
            ("cold", cold),
            ("warm", warm),
        ]:
            path = RESULTS_DIR / f"{name}.jsonl"
            with path.open(
                "w", encoding="utf-8"
            ) as f:
                for row in rows:
                    f.write(
                        json.dumps(
                            row, ensure_ascii=False
                        ) + "\n"
                    )

        summary_path = RESULTS_DIR / "summary.json"
        summary_path.write_text(
            json.dumps(
                summary,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        print("\n=== FINAL KPI SUMMARY ===")
        print(json.dumps(
            summary,
            indent=2,
            ensure_ascii=False,
        ))

        print("\nSUCCESS: Cold/warm evaluation completed.")
        print("Results saved in:", RESULTS_DIR)

    finally:
        cache.close()
        store.client.close()


if __name__ == "__main__":
    main()
