# Week 10 — RAG Caching and Knowledge Lifecycle KPI Snapshot

## Evaluation configuration

- Collection: `capstone_chunks_v10`
- KB version: `v2.w10.2`
- Retrieval: dense, top-3
- Golden set: 20 questions
- Evaluation: 20 cold queries followed by 20 identical warm queries
- Cache: SQLite semantic response cache, exact-match path exercised

## Measured performance

| KPI | Cold | Warm |
|---|---:|---:|
| Retrieval hit rate @3 | 100% | 100%* |
| Cache hit rate | 0% | 100% |
| Exact cache hits | 0 | 20 |
| Mean latency | 2453.55 ms | 0.25 ms |
| p50 latency | 2174 ms | 0 ms |
| p95 latency | 3384 ms | 0 ms |
| Total estimated chat cost | $0.00151245 | $0.00000000 |

*Warm retrieval hits are inherited from cached responses; no fresh retrieval occurred.

Answer consistency: 100%.

Warm-pass latency is reported at integer-millisecond resolution. A displayed
0 ms does not mean zero execution time.

Embedding costs are excluded from the reported chat costs.

## Manual answer-quality review

The 20 cold answers were compared with the golden-set ideal answers.

| Classification | Questions | Count |
|---|---|---:|
| Fully correct | All except q09, q10, q12, q14, q17 | 15 |
| Partially correct | q12, q14 | 2 |
| Incorrect against golden answers | q09, q10, q17 | 3 |

Provisional strict task success: **15/20 = 75%**.

This is a manual golden-answer comparison, not a RAGAS measurement.

## Failure analysis

### q09 — Currency/reference mismatch
The indexed expense policy states USD 80 for US travel.
The golden answer expects GBP 80.
The generated answer follows the indexed evidence.

### q10 — Missing receipt deadline
The golden answer expects submission within 30 days.
The indexed expense-policy text does not contain that deadline.
The stored Page 1 text contains incomplete sentences.

### q12 — Training approval threshold
The golden answer requires Director approval beyond GBP 1,000.
The indexed Page 1 text is truncated after 'approvals beyond GB'.
The generated answer omits the exact threshold.

### q14 — Incomplete answer synthesis
The retrieved VPN policy contains extension 4040 and weekday
helpdesk hours 08:00–18:00.
The generated answer supplies the extension but omits the hours.

### q17 — Redaction and answerability conflict
The golden answer expects a telephone number.
The indexed security policy contains [PHONE].
The generated answer appropriately avoids inventing the redacted value.

## Knowledge lifecycle verification

A synthetic policy was updated from INR 12,000 to INR 18,000.

Observed behavior:
- Old chunk tombstoned
- Replacement chunk indexed
- Response cache invalidated
- KB version advanced
- Post-update answer reflected INR 18,000
- Subsequent identical query served from cache

The synthetic policy was subsequently tombstoned and removed from
the live retrieval set.

Final collection state before benchmark:
- 26 total stored chunks
- 24 live chunks
- 2 tombstoned synthetic chunks
- KB version v2.w10.2

## Architectural decisions and limitations

1. Preserve source-grounded answers even when a golden reference disagrees.
2. Do not restore redacted personal or contact information solely to improve scores.
3. Treat retrieval hit rate and answer correctness as separate metrics.
4. Validate source completeness before changing retrieval parameters.
5. Cache invalidation and KB versioning are necessary to prevent stale answers.
6. Exact repeated-question caching was tested; semantic paraphrase hit rate
   was not measured in this benchmark.
7. The original expense-policy PDF was unavailable during root-cause analysis.
   The origin of the truncated indexed text remains unresolved.
8. The benchmark is a controlled 20-question test, not a production workload.

## Evidence

- `results/wk10/cold.jsonl`
- `results/wk10/warm.jsonl`
- `results/wk10/summary.json`
- Week 10 document-update and cache-invalidation tests

## Next actions

- Add ingestion-integrity regression tests.
- Investigate source-document completeness when the original PDF is available.
- Document cache and lifecycle design in an ADR and operational runbook.
- Complete final test suite, repository review, and pull request.
