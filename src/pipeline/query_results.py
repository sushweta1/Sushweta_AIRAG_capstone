"""Query persisted pipeline runs and answers.

Usage:
    python -m src.pipeline.query_results --runs
    python -m src.pipeline.query_results
    python -m src.pipeline.query_results RAG
"""

import sqlite3
import sys


def show_runs(con: sqlite3.Connection) -> None:
    print(
        f"{'id':>4} {'started':>12} {'questions':>10} "
        f"{'retries':>8} {'cost_usd':>10} {'fail':>6} {'fake':>5}"
    )

    for row in con.execute(
        """
        SELECT
            id,
            started_at,
            n_questions,
            n_retries_total,
            total_cost_usd,
            fail_rate,
            use_fake
        FROM runs
        ORDER BY id DESC
        """
    ):
        print(
            f"{row[0]:>4} "
            f"{row[1]:>12.1f} "
            f"{row[2]:>10} "
            f"{row[3]:>8} "
            f"{row[4]:>10.4f} "
            f"{row[5]:>6.2f} "
            f"{row[6]:>5}"
        )

def search_answers(con: sqlite3.Connection, pattern: str) -> None:
    rows = con.execute(
        """
        SELECT
            id,
            run_id,
            retries,
            question,
            answer
        FROM answers
        WHERE question LIKE ?
        ORDER BY id
        """,
        (f"%{pattern}%",),
    )

    for row in rows:
        print(
            f"[#{row[0]} run={row[1]} retries={row[2]}] "
            f"{row[3]}\n→ {row[4][:140]}"
        )

def main() -> None:
    con = sqlite3.connect("results.db")

    if len(sys.argv) > 1 and sys.argv[1] == "--runs":
        show_runs(con)
    else:
        pattern = sys.argv[1] if len(sys.argv) > 1 else ""
        search_answers(con, pattern)

    con.close()


if __name__ == "__main__":
    main()