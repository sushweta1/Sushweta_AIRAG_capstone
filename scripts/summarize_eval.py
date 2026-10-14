import sqlite3

from src.pipeline.settings import Settings


RUN_LABEL = "eval-run-001"

conn = sqlite3.connect(Settings().results_db)

summary = conn.execute(
    """
    SELECT
        COUNT(*),
        AVG(accuracy),
        AVG(groundedness),
        AVG(format)
    FROM eval_runs
    WHERE eval_run_label = ?
    """,
    (RUN_LABEL,),
).fetchone()

lowest = conn.execute(
    """
    SELECT
        golden_id,
        accuracy,
        groundedness,
        format,
        reasoning
    FROM eval_runs
    WHERE eval_run_label = ?
    ORDER BY (accuracy + groundedness + format), golden_id
    LIMIT 5
    """,
    (RUN_LABEL,),
).fetchall()

conn.close()

print(f"Run: {RUN_LABEL}")
print(f"Total evaluations: {summary[0]}")
print(f"Average accuracy: {summary[1]:.2f}")
print(f"Average groundedness: {summary[2]:.2f}")
print(f"Average format: {summary[3]:.2f}")

print("\nLowest-scoring evaluations:")
for golden_id, accuracy, groundedness, format_score, reasoning in lowest:
    print(
        f"\n{golden_id}: "
        f"A={accuracy}, G={groundedness}, F={format_score}"
    )
    print(f"Reason: {reasoning}")