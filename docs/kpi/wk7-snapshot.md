# Week 7 — Qdrant RAG KPI Snapshot

## 1. Implementation Overview

Application: FastAPI Knowledge Assistant

Week 7 objective:
Migrate the Week 6 JSON-based RAG implementation to Qdrant Cloud
while preserving the existing FastAPI application contract.

### Corpus and Embeddings

- Source documents: 16 FastAPI Markdown files
- Indexed chunks: 303
- Chunk size: 500 characters
- Chunk overlap: 50 characters
- Embedding model: text-embedding-3-small
- Embedding dimensions: 1536
- Generation model: gpt-4o-mini
- Retrieval depth: Top-K = 5

### Vector Storage

Week 6:
- Local JSON embedding index
- Linear cosine similarity search

Week 7:
- Qdrant Cloud vector database
- Collection: capstone_chunks
- Distance metric: Cosine
- Stored vectors: 303
- Retrieval API: query_points()

The original JSON embedding index and naive RAG implementation
have been preserved for comparison.

## 2. Qdrant Migration

Migration script:
scripts/migrate_to_qdrant.py

Qdrant store module:
src/rag/qdrant_store.py

Qdrant RAG module:
src/rag/qdrant_rag.py

Migration results:
- 303 chunks loaded from the Week 6 embedding index
- 303 vectors uploaded successfully
- Collection size verified as 303 points
- Existing unrelated Qdrant collections preserved

## 3. Application Integration

Updated:
src/api/main.py

Validation:
- GET /health: HTTP 200
- POST /ask_batched: HTTP 200
- Qdrant retrieval: Successful
- Answer generation: Successful
- Source citations: Present
- SQLite persistence: Successful
- Existing Answer schema: Preserved

The /ask_batched endpoint now uses Qdrant retrieval.

The /ask streaming endpoint retains its existing streaming
implementation and has not been migrated to Qdrant.

## 4. Golden-Set Evaluation

Dataset:
data/golden_set.jsonl

Total questions: 20

Candidate model: gpt-4o-mini
Judge model: gpt-4o-mini

Week 6 evaluation:
eval-run-wk6-rag-001

Week 7 evaluation:
eval-run-wk7-qdrant-001

Scores range from 1 to 4.

| Metric | Week 6 RAG | Week 7 Qdrant | Change |
|---|---:|---:|---:|
| Accuracy | 3.05 | 3.10 | +0.05 |
| Groundedness | 3.15 | 3.15 | 0.00 |
| Format | 3.30 | 3.35 | +0.05 |
| Overall average | 3.17 | 3.20 | +0.03 |

All 20 Week 7 evaluation results were saved to SQLite.

## 5. Evaluation Findings

The Qdrant implementation achieved an overall average of 3.20/4,
compared with the Week 6 baseline of 3.17/4.

The difference is small and does not demonstrate that Qdrant
independently improved answer quality.

The two implementations use the same corpus, chunking strategy,
embedding model, and default retrieval depth.

The Week 7 generation prompt also differs from Week 6, and
LLM-generated answers and judge scores may vary between runs.

### Low-Scoring Questions

g012:
How can you add validation constraints to a FastAPI query parameter?

Week 7 scores:
- Accuracy: 1
- Groundedness: 1
- Format: 1

Finding:
The existing corpus lacks sufficient documentation about
query validation constraints.

g014:
How can the same FastAPI dependency be reused across multiple
path operations?

Week 7 scores:
- Accuracy: 1
- Groundedness: 1
- Format: 2

Finding:
The relevant documentation was not consistently retrieved
within the default Top-K = 5 results.

The Week 6 experiment showed that increasing Top-K to 10
retrieved a relevant dependency-reuse chunk.

## 6. Cost and Token Usage

Example Qdrant-backed API request:

Question:
How do I define a path parameter in FastAPI?

- HTTP status: 200
- Retrieved chunks: 5
- Reported generation cost: approximately $0.000196
- Confidence: 1.0 (fixed placeholder)

Reported cost covers chat generation only.
Query embedding cost is excluded.

## 7. Known Limitations

1. Fixed-character chunking can split sentences.
2. Raw Markdown contains unresolved code-example directives.
3. The corpus has documentation coverage gaps.
4. Top-K = 5 may miss relevant evidence.
5. The sources field lists retrieved chunks, not necessarily cited chunks.
6. Reported API cost excludes query embedding.
7. Confidence is hardcoded rather than calibrated.
8. The streaming /ask endpoint does not use Qdrant retrieval.
9. A controlled latency comparison has not yet been completed.
10. LLM-judge scores are subject to evaluation variability.

## 8. Improvement Opportunities

1. Add missing FastAPI documentation for query validation.
2. Improve chunk boundaries and Markdown preprocessing.
3. Compare Top-K = 5 and Top-K = 10.
4. Investigate retrieval ranking for g012 and g014.
5. Measure Qdrant retrieval latency across multiple requests.
6. Evaluate citation accuracy separately.
7. Include embedding costs in total request cost.
8. Consider migrating the streaming endpoint to Qdrant.
9. Repeat the golden-set evaluation after improvements.

## 9. Conclusion

Week 7 successfully migrated the FastAPI Knowledge Assistant
from a local JSON vector index to Qdrant Cloud.

All 303 embeddings were migrated successfully.

The Qdrant RAG pipeline, FastAPI integration, and SQLite
persistence were validated.

All 20 golden questions were evaluated using the existing
LLM-judge framework.

The overall evaluation score remained comparable to Week 6,
increasing from 3.17 to 3.20 out of 4.

The primary achievement is successful vector database
integration while preserving existing application functionality.
