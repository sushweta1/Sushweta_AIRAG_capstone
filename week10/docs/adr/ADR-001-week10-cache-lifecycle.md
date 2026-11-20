# ADR-001: Version-Aware Semantic Caching and Knowledge Lifecycle

- Status: Accepted for Week 10 capstone baseline
- Date: 2026-11-20
- Scope: Week 10 RAG pipeline
- Collection: `capstone_chunks_v10`
- Baseline KB version: `v2.w10.2`

## 1. Context and problem

The RAG assistant must provide grounded answers while minimizing
repeated LLM calls and preventing outdated or deleted knowledge
from influencing responses.

Two related risks must be addressed:

1. Repeated questions incur unnecessary retrieval and generation cost.
2. Document updates can leave stale vectors, cached answers, or
   retrieval indexes containing superseded information.

Caching improves performance but can amplify correctness problems
if stale or incorrect answers are reused.

## 2. Decision

Adopt version-aware semantic response caching together with
soft deletion, live-only retrieval, and controlled document updates.

The implementation uses:

- SQLite-backed response cache
- Exact-match lookup before semantic similarity lookup
- Cosine similarity threshold of 0.95 for semantic cache reuse
- Cache scope incorporating KB version and relevant pipeline settings
- Tombstones represented by `deleted_at`
- Live-only filtering for retrieval
- Document replacement with cache invalidation
- Persistent KB-version advancement after updates
- Dense retrieval as the default evaluated retrieval strategy

## 3. Alternatives considered

### A. No response caching

Advantages:
- Always performs fresh retrieval and generation
- Avoids stale response-cache entries

Disadvantages:
- Higher repeated-query latency
- Repeated LLM generation cost

Decision: Rejected as the default.

### B. Exact-match caching only

Advantages:
- Simple and predictable
- Low risk of incorrectly treating different questions as equivalent

Disadvantages:
- Cannot reuse responses for paraphrased questions

Decision: Retained as the first lookup path, supplemented by semantic matching.

### C. Semantic caching with a lower threshold

Advantages:
- Potentially higher hit rate for paraphrases

Disadvantages:
- Greater risk of reusing answers for questions with different meanings
- Numeric and policy-sensitive questions are particularly vulnerable

Decision: Use a conservative 0.95 threshold.

### D. Hard deletion and full collection rebuilds

Advantages:
- Removes obsolete vectors physically
- Can simplify some retrieval semantics

Disadvantages:
- Greater operational disruption
- More expensive rebuilds
- Reduced ability to inspect superseded document history

Decision: Prefer tombstones and targeted document updates.

### E. Tombstones without retrieval filtering

Advantages:
- Simpler update implementation

Disadvantages:
- Deleted documents can still influence answers
- Hybrid and sparse retrieval may retain stale evidence

Decision: Rejected.

### F. Cache invalidation without KB versioning

Advantages:
- Fewer cache-key dimensions

Disadvantages:
- Invalidation failures may permit stale answers
- Harder to distinguish answers generated from different KB states

Decision: Use both explicit invalidation and version-aware scope.

## 4. Implementation

### Response caching

The cache checks for an exact question match first.

For eligible queries without an exact match, it may compare
question embeddings using cosine similarity.

The default semantic reuse threshold is 0.95.

Cache entries are scoped to the KB version and relevant
retrieval/generation configuration.

Caching is bypassed for unsupported query configurations.

### Knowledge lifecycle

Document updates:

1. Validate the target document and collection.
2. Parse, chunk, redact, and embed replacement content.
3. Invalidate response-cache entries.
4. Tombstone superseded chunks.
5. Insert replacement chunks.
6. Verify the new live state.
7. Invalidate the cache again.
8. Advance the persistent KB version.

The implementation includes rollback attempts for failures.
It does not guarantee atomic updates across Qdrant, SQLite,
and the KB-version file.

### Retrieval

Dense and hybrid retrieval paths must exclude tombstoned chunks.

Sparse retrieval data must be rebuilt or refreshed from live
content to avoid using deleted evidence.

## 5. Measured evidence

Week 10 evaluation:

- Golden questions: 20
- Retrieval: dense, top-3
- Expected-source retrieval hit rate: 100%
- Cold cache hit rate: 0%
- Warm exact cache hit rate: 100%
- Cold mean latency: 2453.55 ms
- Warm mean latency: 0.25 ms
- Cold p50/p95 latency: 2174/3384 ms
- Warm p50/p95 latency: reported 0/0 ms
- Cold estimated chat cost: USD 0.00151245 total
- Warm additional chat cost: USD 0
- Cold/warm answer consistency: 100%
- Provisional strict answer success: 75%

These results demonstrate exact repeated-question cache behavior.
They do not establish semantic paraphrase hit rate or production
performance.

Embedding costs are excluded from reported chat costs.

## 6. Knowledge freshness evidence

A synthetic policy was initially indexed with an annual
allowance of INR 12,000.

The document was updated to INR 18,000.

Observed results:

- Old chunk tombstoned
- Replacement chunk indexed
- Cache invalidated
- KB version advanced
- Same question answered INR 18,000 after update
- Subsequent identical question served from cache

The synthetic document was subsequently removed from the live
retrieval set while retaining tombstoned history.

The final benchmark used 24 live chunks and two tombstones.

## 7. Trade-offs

| Decision | Benefit | Cost or risk |
|---|---|---|
| Semantic threshold 0.95 | Conservative reuse | May miss valid paraphrases |
| SQLite response cache | Simple local persistence | Limited multi-instance coordination |
| Exact lookup first | Very low repeated-query latency | Only helps identical questions |
| Tombstones | Preserve history | Require consistent filtering |
| Live-only hybrid retrieval | Avoid stale sparse evidence | BM25 rebuild overhead |
| Explicit cache invalidation | Reduces stale-answer risk | Additional update coordination |
| KB version in cache scope | Isolates KB generations | Requires reliable version advancement |
| Dense retrieval default | Matches evaluated baseline | May miss lexical edge cases |

## 8. Risks and uncertainties

### Cache correctness

An incorrect generated answer can be cached and repeated.

The 20-question evaluation found 100% answer consistency but
only 75% provisional strict answer success.

### Semantic matching

The benchmark exercised exact hits, not semantic paraphrases.
The threshold requires further evaluation using paraphrase
and near-miss pairs.

### Concurrent updates

Document replacement, cache invalidation, and version
advancement are not one atomic transaction.

Concurrent readers may observe intermediate states.

### Source completeness

The indexed expense policy contains truncated passages.
The original PDF was unavailable during investigation.

The root cause remains unresolved.

### Redaction and answerability

The security hotline was redacted to `[PHONE]`.
The golden set expects a specific telephone number.

The evaluation must distinguish protected information from
genuine retrieval or generation failures.

### Measurement

The benchmark is small and controlled.

Reported 0 ms warm latencies reflect measurement resolution,
not literally instantaneous execution.

## 9. Consequences

Positive:
- Lower latency for repeated questions
- Avoidance of repeated chat-generation cost on cache hits
- Reduced risk of stale answers after controlled updates
- Retained document history through tombstones
- Clearer separation of retrieval, freshness, and correctness KPIs

Negative:
- More complex cache and KB lifecycle management
- Potential cache false positives and false negatives
- Need for consistent tombstone filtering across retrieval paths
- Operational complexity during concurrent document updates

## 10. Reviewer agreement requested

Reviewers are asked to agree that:

1. Version-aware caching and explicit invalidation are necessary.
2. Tombstoned content must never be eligible for live retrieval.
3. Exact caching is validated; semantic caching requires further testing.
4. The current implementation is a capstone baseline, not a
   fully transactional production architecture.
5. Retrieval coverage and answer correctness must be measured separately.

## 11. Follow-up decisions

- Define acceptable semantic false-positive rate.
- Determine whether cache invalidation should use distributed coordination.
- Define atomic or staged document-publication semantics.
- Establish source-integrity checks before indexing.
- Define redaction-aware evaluation rules.
- Add representative concurrency and load testing.

## 12. References

- `docs/kpi/wk10-snapshot.md`
- `src/rag/cache.py`
- `src/rag/kb_version.py`
- `src/rag/qdrant_rag.py`
- `src/rag/qdrant_store.py`
- `src/rag/retrieval.py`
- `src/ingest/pipeline.py`
- `scripts/update_document.py`
- `scripts/evaluate_w10.py`
