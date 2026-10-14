from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

from src.eval.golden import load_golden_set
from src.eval.pairwise import pairwise_compare_with_flip
from src.pipeline.models import Question
from src.pipeline.pipeline import ask_llm
from src.pipeline.settings import Settings


PROMPT_V1_PATH = Path("data/prompt-v1.txt")
PROMPT_V2_PATH = Path("data/prompt-v2.txt")
GOLDEN_SET_PATH = Path("data/golden_set.jsonl")
OUTPUT_PATH = Path("data/pairwise-001-results.json")


async def main() -> None:
    settings = Settings()

    prompt_v1 = PROMPT_V1_PATH.read_text(encoding="utf-8").strip()
    prompt_v2 = PROMPT_V2_PATH.read_text(encoding="utf-8").strip()

    rows = load_golden_set(GOLDEN_SET_PATH)

    results = []
    start = time.perf_counter()

    for index, row in enumerate(rows, start=1):
        print(f"[{index}/{len(rows)}] {row['id']}")

        question = Question(question=row["question"])

        answer_v1 = await ask_llm(
            question,
            settings,
            system_prompt=prompt_v1 or None,
        )

        answer_v2 = await ask_llm(
            question,
            settings,
            system_prompt=prompt_v2 or None,
        )

        comparison = await pairwise_compare_with_flip(
            row["question"],
            row["ideal_answer"],
            answer_v1.content,
            answer_v2.content,
            settings,
        )

        results.append(
            {
                "id": row["id"],
                "question": row["question"],
                "ideal_answer": row["ideal_answer"],
                "answer_v1": answer_v1.content,
                "answer_v2": answer_v2.content,
                **comparison,
            }
        )

        print(f"Winner: {comparison['overall_winner']}")

    elapsed = time.perf_counter() - start

    position_bias_count = 0

    for r in results:
        forward = r["forward"]["winner"]
        reverse = r["reverse"]["winner"]

        if forward == reverse and forward != "tie":
            position_bias_count += 1

    summary = {
        "v1_wins": sum(r["overall_winner"] == "v1" for r in results),
        "v2_wins": sum(r["overall_winner"] == "v2" for r in results),
        "ties": sum(r["overall_winner"] == "tie" for r in results),
        "ambiguous": sum(
            r["overall_winner"] == "ambiguous" for r in results
        ),
        "wall_clock_seconds": round(elapsed, 2),
        "position_bias_rate": round(
            position_bias_count / len(results) * 100, 1
        ),
    }

    output = {
        "summary": summary,
        "results": results,
    }

    OUTPUT_PATH.write_text(
        json.dumps(output, indent=2),
        encoding="utf-8",
    )

    print()
    print("Summary:")
    print(json.dumps(summary, indent=2))
    print(f"\nSaved: {OUTPUT_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
    