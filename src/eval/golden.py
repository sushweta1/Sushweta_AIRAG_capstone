from __future__ import annotations

import json
from pathlib import Path


REQUIRED_FIELDS = {"id", "question", "ideal_answer", "notes"}


def load_golden_set(path: str | Path) -> list[dict]:
    path = Path(path)

    rows: list[dict] = []

    with path.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            line = line.strip()

            if not line:
                continue

            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON on line {line_number}: {exc}"
                ) from exc

            missing = REQUIRED_FIELDS - row.keys()
            if missing:
                raise ValueError(
                    f"Line {line_number} is missing fields: {sorted(missing)}"
                )

            rows.append(row)

    return rows


def validate_golden_set(rows: list[dict]) -> None:
    if len(rows) != 20:
        raise ValueError(f"Expected 20 golden-set entries, found {len(rows)}")

    ids = [row["id"] for row in rows]

    if len(ids) != len(set(ids)):
        raise ValueError("Golden-set IDs must be unique")

    expected_ids = [f"g{i:03d}" for i in range(1, 21)]

    if ids != expected_ids:
        raise ValueError(
            f"Expected IDs g001 through g020 in order, found: {ids}"
        )

    happy = sum("happy-path" in row["notes"].lower() for row in rows)
    harder = sum("harder" in row["notes"].lower() for row in rows)
    edge = sum("edge" in row["notes"].lower() for row in rows)

    if (happy, harder, edge) != (14, 4, 2):
        raise ValueError(
            "Expected 14 happy-path, 4 harder, and 2 edge entries; "
            f"found {happy}, {harder}, {edge}"
        )


if __name__ == "__main__":
    golden_path = Path("data/golden_set.jsonl")

    rows = load_golden_set(golden_path)
    validate_golden_set(rows)

    print(f"Golden set valid: {len(rows)} entries")
    print("Distribution: 14 happy-path, 4 harder, 2 edge")