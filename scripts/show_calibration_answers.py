import sqlite3

IDS = [
    "g001", "g004", "g007", "g010", "g012",
    "g014", "g015", "g016", "g018", "g020",
]

conn = sqlite3.connect("results.db")
cur = conn.cursor()

for gid in IDS:
    cur.execute(
        """
        SELECT golden_id, question, ideal_answer, candidate_answer
        FROM eval_runs
        WHERE eval_run_label = 'eval-run-001'
          AND golden_id = ?
        """,
        (gid,),
    )

    row = cur.fetchone()

    if row:
        golden_id, question, ideal, candidate = row

        print("=" * 70)
        print(f"ID: {golden_id}")
        print(f"\nQUESTION:\n{question}")
        print(f"\nIDEAL ANSWER:\n{ideal}")
        print(f"\nCANDIDATE ANSWER:\n{candidate}")
        print()

conn.close()