from __future__ import annotations

import asyncio
import json

from src.eval.pairwise import pairwise_compare_with_flip
from src.pipeline.settings import Settings


CASE_IDS = {"g005", "g006"}


async def main() -> None:
    settings = Settings()

    with open(
        "data/pairwise-001-results.json",
        "r",
        encoding="utf-8",
    ) as f:
        data = json.load(f)

    for row in data["results"]:
        if row["id"] not in CASE_IDS:
            continue

        print("\n" + "=" * 60)
        print(row["id"], "-", row["question"])

        result = await pairwise_compare_with_flip(
            row["question"],
            row["ideal_answer"],
            row["answer_v1"],
            row["answer_v2"],
            settings,
        )

        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())