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

    row = rows[0]

    print(f"Evaluating {row['id']}: {row['question']}")

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

    print(f"Saved eval row: {rowid}")

    print("Candidate:", candidate.content)
    print("Verdict:", verdict.model_dump())

if __name__ == "__main__":
    asyncio.run(run_evaluation())