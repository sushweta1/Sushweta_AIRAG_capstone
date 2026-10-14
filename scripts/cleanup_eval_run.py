import sqlite3

from src.pipeline.settings import Settings


conn = sqlite3.connect(Settings().results_db)

deleted = conn.execute(
    "DELETE FROM eval_runs WHERE eval_run_label = 'eval-run-001'"
).rowcount

conn.commit()
conn.close()

print(f"Deleted eval-run-001 rows: {deleted}")