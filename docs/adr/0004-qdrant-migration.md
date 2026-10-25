# ADR 0004: Migration from Local JSON RAG to Qdrant Cloud

## Status

Accepted as the Week 7 architecture.

## Context

The Week 6 FastAPI Knowledge Assistant implemented
Retrieval-Augmented Generation using a local JSON embedding index.

The system contained:

- 16 FastAPI documentation files
- 303 indexed chunks
- 1536-dimensional embeddings
- Cosine similarity retrieval
- Top-K = 5
- gpt-4o-mini for answer generation

The Week 6 approach was functional but relied on loading
embeddings from a JSON file and performing brute-force
similarity calculations.

This approach was suitable for a small corpus but presented
limitations for larger-scale vector storage and retrieval.

Week 7 introduces Qdrant Cloud as the vector database.

## Decision

Migrate vector storage and retrieval to Qdrant Cloud while
preserving the existing FastAPI application contract.

### Vector Database

Use Qdrant Cloud with the following configuration:

- Collection: capstone_chunks
- Vector dimensions: 1536
- Distance metric: Cosine
- Embedding model: text-embedding-3-small
- Indexed points: 303

The existing Week 6 embeddings are reused rather than
regenerated during migration.

### Migration

Implement:

- src/rag/qdrant_store.py
- scripts/migrate_to_qdrant.py

The migration script loads the existing JSON embedding index
and uploads its vectors and metadata into Qdrant Cloud.

The original JSON index is preserved.

### Retrieval and Generation

Implement:

- src/rag/qdrant_rag.py

For each question:

1. Generate a query embedding.
2. Search the Qdrant collection using query_points().
3. Retrieve the five highest-ranked chunks by default.
4. Supply retrieved context to gpt-4o-mini.
5. Return the answer and retrieved source identifiers.

### API Integration

Update POST /ask_batched to use the Qdrant-backed RAG pipeline.

Preserve:

- Existing Answer response schema
- SQLite answer persistence
- GET /health
- Existing POST /ask streaming implementation

The streaming endpoint is not migrated to Qdrant in Week 7.

## Alternatives Considered

### Continue Using Local JSON

Advantages:
- Simple implementation
- No external vector database dependency
- Easy to inspect and reproduce

Disadvantages:
- Brute-force similarity search
- Local embedding-index management
- Limited scalability as the corpus grows

### Use Qdrant Cloud

Advantages:
- Dedicated vector database
- Server-side similarity retrieval
- Structured vector and payload storage
- Better foundation for expanding the corpus

Disadvantages:
- Requires external service availability
- Requires Qdrant credentials
- Introduces network latency and operational dependencies
- Does not automatically improve retrieval relevance

## Evaluation

The existing 20-question golden set was used to evaluate
the Week 7 implementation.

Candidate model: gpt-4o-mini
Judge model: gpt-4o-mini

Week 7 evaluation label:
eval-run-wk7-qdrant-001

| Metric | Week 6 JSON RAG | Week 7 Qdrant RAG |
|---|---:|---:|
| Accuracy | 3.05 | 3.10 |
| Groundedness | 3.15 | 3.15 |
| Format | 3.30 | 3.35 |
| Overall average | 3.17 | 3.20 |

All scores use a four-point scale.

The Qdrant implementation maintained comparable answer
quality, with a small increase in the overall average.

This difference does not establish that Qdrant itself
improved answer quality.

The Week 7 generation prompt differs from Week 6,
and LLM-generated answers and judge scores may vary.

## Known Retrieval Limitations

### g012: Query Parameter Validation

Scores:
- Accuracy: 1
- Groundedness: 1
- Format: 1

The documentation corpus lacks sufficient information
about FastAPI query validation constraints.

Migrating the same corpus to Qdrant does not resolve
missing source information.

### g014: Dependency Reuse

Scores:
- Accuracy: 1
- Groundedness: 1
- Format: 2

The relevant documentation was not consistently retrieved
within the default Top-K = 5 results.

The Week 6 investigation found the relevant chunk at rank 9.

Increasing retrieval depth or improving ranking may help.

## Consequences

### Positive

- Qdrant Cloud successfully stores all 303 vectors.
- Vector retrieval operates through Qdrant.
- The existing FastAPI response contract is preserved.
- SQLite answer and evaluation persistence remain functional.
- The Week 6 implementation remains available for comparison.
- All 20 golden-set questions were evaluated successfully.

### Limitations

- External Qdrant service dependency
- Query embedding cost excluded from reported API cost
- Retrieval-quality issues remain for some questions
- Fixed-character chunking remains unchanged
- Streaming endpoint still uses its existing implementation
- Controlled latency and scalability benchmarks are pending

## Future Improvements

1. Improve documentation coverage.
2. Test alternative chunking strategies.
3. Compare Top-K = 5 and Top-K = 10.
4. Investigate retrieval ranking.
5. Measure Qdrant retrieval latency.
6. Include embedding costs in request cost calculations.
7. Improve citation accuracy.
8. Consider Qdrant integration for streaming responses.
9. Repeat evaluation after retrieval improvements.

## References

- docs/adr/0003-rag-architecture.md
- docs/kpi/wk6-snapshot.md
- docs/kpi/wk7-snapshot.md
- src/rag/qdrant_store.py
- src/rag/qdrant_rag.py
- scripts/migrate_to_qdrant.py
