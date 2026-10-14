from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from src.eval.golden import load_golden_set
from src.eval.judge import judge_answer
from src.pipeline.settings import Settings
from src.pipeline.store import connect, save_eval_result
from src.rag.naive_rag import CHAT_MODEL, ask_rag, load_index


EVAL_RUN_LABEL = "eval-run-wk6-rag-001"
INDEX_PATH = Path("data/embeddings.json")


async def run_evaluation(limit: int) -> None:
    settings = Settings()
    rows = load_golden_set("data/golden_set.jsonl")

    if limit < 1:
        raise ValueError("limit must be at least 1")

    # Find questions already evaluated in this run.
    with connect(settings.results_db) as conn:
        completed_ids = {
            record[0]
            for record in conn.execute(
                """
                SELECT DISTINCT golden_id
                FROM eval_runs
                WHERE eval_run_label = ?
                """,
                (EVAL_RUN_LABEL,),
            ).fetchall()
        }

    # Select only questions that have not been evaluated.
    remaining_rows = [
        row for row in rows
        if row["id"] not in completed_ids
    ]

    selected_rows = remaining_rows[:limit]

    print(f"Already evaluated: {len(completed_ids)}")
    print(f"Remaining questions: {len(remaining_rows)}")

    print(f"Golden-set entries: {len(rows)}")
    print(f"Questions selected: {len(selected_rows)}")
    print(f"Candidate model: {CHAT_MODEL}")
    print(f"Judge model: {settings.model}")
    print(f"Evaluation run: {EVAL_RUN_LABEL}")

    # Load the existing index; do not rebuild embeddings.
    index = load_index(INDEX_PATH)
    print(f"Loaded indexed chunks: {len(index)}")

    for number, row in enumerate(selected_rows, start=1):
        print()
        print(f"[{number}/{len(selected_rows)}] {row['id']}")
        print(f"Question: {row['question']}")

        # ask_rag is synchronous, so run it in a worker thread.
        candidate = await asyncio.to_thread(
            ask_rag,
            row["question"],
            index,
            settings,
        )

        verdict = await judge_answer(
            question=row["question"],
            candidate_answer=candidate["answer"],
            ideal_answer=row["ideal_answer"],
            settings=settings,
        )

        with connect(settings.results_db) as conn:
            rowid = save_eval_result(
                conn,
                golden_id=row["id"],
                question=row["question"],
                candidate_answer=candidate["answer"],
                ideal_answer=row["ideal_answer"],
                candidate_model=CHAT_MODEL,
                judge_model=settings.model,
                accuracy=verdict.accuracy,
                groundedness=verdict.groundedness,
                format=verdict.format,
                reasoning=verdict.reasoning,
                eval_run_label=EVAL_RUN_LABEL,
            )

        print(
            f"Scores: accuracy={verdict.accuracy}, "
            f"groundedness={verdict.groundedness}, "
            f"format={verdict.format}"
        )
        print(f"Saved evaluation row: {rowid}")

    print()
    print("Week 6 RAG evaluation complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--limit",
        type=int,
        default=1,
        help="Number of golden-set questions to evaluate",
    )
    args = parser.parse_args()

    asyncio.run(run_evaluation(args.limit))
