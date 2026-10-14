from __future__ import annotations

import asyncio

from src.eval.golden import load_golden_set
from src.eval.judge import judge_answer
from src.pipeline.models import Question
from src.pipeline.pipeline import ask_llm
from src.pipeline.settings import Settings
from src.pipeline.store import connect, save_eval_result


EVAL_RUN_LABEL = "eval-run-001"


async def run_evaluation() -> None:
    settings = Settings()
    rows = load_golden_set("data/golden_set.jsonl")

    print(f"Loaded {len(rows)} golden-set entries")
    print(f"Candidate model: {settings.model}")
    print(f"Eval run: {EVAL_RUN_LABEL}")

    for index, row in enumerate(rows, start=1):
        print()
        print(f"[{index}/{len(rows)}] Evaluating {row['id']}")
        print(f"Question: {row['question']}")

        candidate = await ask_llm(
            Question(question=row["question"]),
            settings,
        )

        verdict = await judge_answer(
            question=row["question"],
            candidate_answer=candidate.content,
            ideal_answer=row["ideal_answer"],
            settings=settings,
        )

        with connect(settings.results_db) as conn:
            rowid = save_eval_result(
                conn,
                golden_id=row["id"],
                question=row["question"],
                candidate_answer=candidate.content,
                ideal_answer=row["ideal_answer"],
                candidate_model=settings.model,
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
        print(f"Saved eval row: {rowid}")

    print()
    print("Evaluation complete.")


if __name__ == "__main__":
    asyncio.run(run_evaluation())