from __future__ import annotations

import asyncio
import json

from src.pipeline.models import Question
from src.pipeline.pipeline import ask_llm
from src.pipeline.settings import Settings


async def main() -> None:
    settings = Settings()

    with open("data/golden_set.jsonl", "r", encoding="utf-8") as f:
        rows = [json.loads(line) for line in f if line.strip()]

    row = next(item for item in rows if item["id"] == "g020")

    with open("data/prompt-v1.txt", "r", encoding="utf-8") as f:
        prompt_v1 = f.read().strip()

    with open("data/prompt-v2.txt", "r", encoding="utf-8") as f:
        prompt_v2 = f.read().strip()

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

    print("QUESTION:")
    print(row["question"])

    print("\nV1:")
    print(answer_v1.content)

    print("\nV2:")
    print(answer_v2.content)


if __name__ == "__main__":
    asyncio.run(main())