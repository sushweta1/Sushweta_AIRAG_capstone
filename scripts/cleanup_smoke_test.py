import sqlite3

from src.pipeline.settings import Settings


conn = sqlite3.connect(Settings().results_db)

deleted = conn.execute(
    "DELETE FROM eval_runs WHERE eval_run_label = 'smoke-test'"
).rowcount

conn.commit()
conn.close()

print(f"Deleted smoke-test rows: {deleted}")