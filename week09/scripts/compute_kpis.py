"""Compute KPI summary from an eval run.

Unchanged from W6 — the JSONL output format is identical, so this
script works without modification.

Usage:
    python scripts/compute_kpis.py --label wk7-baseline
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import _bootstrap  # noqa: F401

import argparse
import json


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", required=True)
    parser.add_argument("--input-dir", default="docs/experiments")
    args = parser.parse_args()

    path = Path(args.input_dir) / f"run_{args.label}.jsonl"
    if not path.exists():
        print(f"ERROR: file not found: {path}")
        return

    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    if not rows:
        print(f"ERROR: no rows in {path}")
        return

    successful = [r for r in rows if r.get("error") is None]
    hits = sum(1 for r in rows if r.get("hit"))
    total = len(rows)
    total_cost = sum(r["cost_usd"] for r in successful) if successful else 0
    mean_cost = total_cost / len(successful) if successful else 0
    latencies = sorted(r["latency_ms"] for r in successful)
    p50 = latencies[len(latencies) // 2] if latencies else 0
    p95 = latencies[max(0, int(len(latencies) * 0.95) - 1)] if latencies else 0

    print(f"\n=== KPI Snapshot — {args.label} ===\n")
    print(f"  Task success rate:    {hits} / {total} ({100*hits/total:.0f}%)")
    print(f"  Grounded response:    N/A  (judged from W11)")
    print(f"  Hallucination rate:   N/A  (inverse of grounded)")
    print(f"  Retrieval hit rate:   {hits} / {total} ({100*hits/total:.0f}%)")
    print(f"  Tool success rate:    N/A  (tools at M3)")
    print(f"  Cost / query:         ${mean_cost:.5f}")
    print(f"  Latency p50 / p95:    {p50}ms / {p95}ms")
    print(f"  Escalation rate:      N/A  (added at M3)")
    print(f"\n  Run: {len(successful)} / {total} successful")
    print(f"  Total chat cost: ${total_cost:.5f}")


if __name__ == "__main__":
    main()
