## Step 5a - Chosen improvement

# Lab 2 — Coding-assistant verification note

## The change
Added a `--limit N` CLI flag to `src/pipeline/pipeline.py` so only the first N questions can be processed during debugging and real-API testing.

## The ask
Add a `--limit N` command-line option to `src/pipeline/pipeline.py`. When provided, process only the first N questions loaded from the CSV. When omitted, preserve the existing behavior and process all questions. Keep the change minimal and do not modify unrelated functionality.

## What it produced
Added an `argparse` import, defined an optional integer `--limit` argument, and sliced the loaded questions when a limit is supplied.

## What I verified before accepting
- Diff read: Only `argparse`, the `--limit` argument, and question slicing were added; no unrelated pipeline logic changed.
- Test run: `python -m src.pipeline.pipeline --limit 3` produced 3 answers.
- Regression test: `python -m src.pipeline.pipeline` using the fake LLM produced all 20 answers.
- Security check: No new dependencies, no changes to API-key or secret handling, and the CLI value is parsed as an integer.

## What I changed before committing
Temporarily enabled the fake LLM for the full 20-question regression test, then restored `use_fake=False` before committing.