import sqlite3

from src.pipeline.settings import Settings


conn = sqlite3.connect(Settings().results_db)

rows = conn.execute(
    """
    SELECT
        id,
        golden_id,
        accuracy,
        groundedness,
        format,
        eval_run_label
    FROM eval_runs
    ORDER BY id
    """
).fetchall()

conn.close()

for row in rows:
    print(row)