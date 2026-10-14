# Week 3 Stress Test Findings

## Finding 1 — Malformed JSON

Tested four invalid request scenarios against `/ask`:

- Empty body → 422 Unprocessable Entity; required `question` field was missing.
- Wrong field name (`q`) → 422; required `question` field was missing.
- Wrong type (`question: 42`) → 422; `question` must be a string.
- Malformed JSON → JSON decode error.

All invalid inputs were rejected by FastAPI/Pydantic validation before reaching the application pipeline or LLM.

## Finding 2 — 5000-character question

A valid request containing a 5000-character question completed successfully.

Observed total wall time: approximately 3.52 seconds.

The API did not hang or return an error. The long input was handled successfully.

## Finding 3 — Disconnect mid-stream

A request was sent with the client configured to disconnect after 1 second.

The client timed out after approximately 1 second with 0 bytes received. The Uvicorn server showed the request but no unhandled exception or traceback.

After the disconnect, `/health` still returned `status: ok`, confirming that the server remained healthy.

## Finding 4 — 50 parallel requests

Stress test configuration:

- Total requests: 50
- Maximum concurrent requests: 10
- Successes: 50 / 50
- Total wall time: 9.00 seconds
- Effective throughput: 5.56 requests/second
- Minimum latency: 0.88 seconds
- p50 latency: 1.56 seconds
- p95 latency: 2.07 seconds
- Maximum latency: 2.29 seconds

All 50 requests completed successfully with no request failures.

SQLite persistence was not verified during this run.

## Known limits / follow-ups

- Long-input behavior should eventually include explicit token-limit handling.
- SQLite behavior under concurrent writes should be verified separately.
- Cost tracking should be reviewed for production usage.
- Client disconnect handling appears stable, but cancellation of downstream work could be investigated further.