from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from src.eval.critic_creator import (
    critique_answer,
    mean_score,
    revise_answer,
)
from src.eval.golden import load_golden_set
from src.pipeline.models import Question
from src.pipeline.pipeline import ask_llm
from src.pipeline.settings import Settings


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--golden-id", required=True)
    parser.add_argument("--max-rounds", type=int, default=3)
    parser.add_argument("--threshold", type=float, default=3.5)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    settings = Settings()

    rows = load_golden_set("data/golden_set.jsonl")
    row = next(r for r in rows if r["id"] == args.golden_id)

    question = row["question"]
    ideal_answer = row["ideal_answer"]

    print(f"Running Critic-Creator on {args.golden_id}")
    print(f"  question    : {question}")
    print(f"  max rounds  : {args.max_rounds}")
    print(f"  convergence : mean >= {args.threshold}")

    initial = await ask_llm(
        Question(question=question),
        settings,
    )

    current_answer = initial.content
    trace = []

    for round_num in range(1, args.max_rounds + 1):
        verdict = await critique_answer(
            question,
            ideal_answer,
            current_answer,
            settings,
        )

        mean = mean_score(verdict)

        print(
            f"  Round {round_num}: "
            f"a={verdict.accuracy} "
            f"g={verdict.groundedness} "
            f"f={verdict.format} "
            f"(mean={mean:.2f})"
        )

        trace.append(
            {
                "round": round_num,
                "answer": current_answer,
                "accuracy": verdict.accuracy,
                "groundedness": verdict.groundedness,
                "format": verdict.format,
                "mean": mean,
                "feedback": verdict.feedback,
            }
        )

        if mean >= args.threshold:
            print("  ✓ CONVERGED")
            break

        current_answer = await revise_answer(
            question,
            ideal_answer,
            current_answer,
            verdict.feedback,
            settings,
        )

    output = Path(args.output)

    lines = [
        "# Critic-Creator Trace",
        "",
        f"Golden ID: {args.golden_id}",
        "",
        f"Question: {question}",
        "",
    ]

    for item in trace:
        lines.extend(
            [
                f"## Round {item['round']}",
                "",
                f"**Answer:** {item['answer']}",
                "",
                (
                    f"**Scores:** Accuracy {item['accuracy']}/4, "
                    f"Groundedness {item['groundedness']}/4, "
                    f"Format {item['format']}/4 "
                    f"(mean {item['mean']:.2f})"
                ),
                "",
                f"**Critic feedback:** {item['feedback']}",
                "",
            ]
        )

    lines.extend(
        [
            "## Final Answer",
            "",
            current_answer,
            "",
        ]
    )

    output.write_text("\n".join(lines), encoding="utf-8")

    print()
    print("Final answer:")
    print(current_answer)
    print()
    print(f"Trace written to {output}")


if __name__ == "__main__":
    asyncio.run(main())