# Week 6 — RAG Baseline KPI Snapshot

## Implementation

- Application: FastAPI Knowledge Assistant
- Corpus: 16 official FastAPI Markdown documents
- Corpus size: 168 KB
- Chunking: 500 characters, 50-character overlap
- Indexed chunks: 303
- Embedding model: text-embedding-3-small
- Embedding dimensions: 1536
- Index storage: Local JSON (9.2 MB)
- Retrieval: Cosine similarity, Top-K = 5
- Generation model: gpt-4o-mini

## Retrieval Evaluation

Test question:
How do I define path parameters in FastAPI?

Top-5 retrieved chunks:
1. query_parameters#6 — 0.6307
2. request_body#12 — 0.6107
3. path_parameters#18 — 0.5929
4. path_parameters#17 — 0.5732
5. first_steps#20 — 0.5723

Observation:
Retrieval returned relevant documentation, but the
most useful introductory passage was not ranked highly.

## Generation Evaluation

- Grounded answer generated successfully
- Source citations present
- Chat input tokens in direct test: 764
- Chat output tokens in direct test: 137
- API endpoint chat cost: $0.0001932
- Query embedding cost: Not included
- Confidence: 1.0 (placeholder, not calibrated)

## Integration Validation

- /health: Passed
- /ask: Passed
- /ask_batched: Passed
- Answer schema: v1 preserved
- SQLite persistence: Passed

## Known Limitations

1. Fixed-size chunks can split sentences.
2. Raw Markdown contains unresolved code-example directives.
3. Top-K retrieval does not always rank the best evidence first.
4. The sources field lists retrieved chunks, not necessarily cited chunks.
5. Reported cost excludes query embedding.
6. Confidence is not calibrated.
7. Full golden-set evaluation is pending.

## Next Steps

- [x] Run the existing 20-question golden set.
- [x] Measure answer quality and groundedness.
- [x] Compare Week 6 results against Week 5.
- [x] Measure initial single-request latency.
- [x] Investigate low-scoring questions (g012 and g014).
- [x] Test retrieval improvement by increasing Top-K from 5 to 10.
- [ ] Improve chunking and source-document preparation.
- [ ] Re-evaluate the complete golden set after improvements.

## Golden-Set Evaluation Results

Evaluation dataset: 20 questions
Judge model: gpt-4o-mini
Score range: 1–4

| Metric | Week 5 LLM | Week 6 RAG | Change |
|---|---:|---:|---:|
| Accuracy | 3.60 | 3.05 | -0.55 |
| Groundedness | 3.80 | 3.15 | -0.65 |
| Format | 3.75 | 3.30 | -0.45 |
| Overall average | 3.72 | 3.17 | -0.55 |

Week 5 run: eval-run-001
Week 6 run: eval-run-wk6-rag-001

## Evaluation Findings

- All 20 golden-set questions were evaluated.
- The RAG pipeline completed successfully.
- Week 6 scores were lower than the Week 5 baseline.
- Questions g012 and g014 scored 1/4 in all dimensions.
- Fixed-character chunking can split sentences and explanations.
- Some downloaded documentation contains unresolved code directives.
- The LLM judge assesses groundedness against reference answers,
  rather than directly verifying retrieved source passages.
- Further investigation is required before attributing score
  differences to specific causes.

## Improvement Opportunities

1. Investigate low-scoring questions g012 and g014.
2. Improve document preprocessing and chunk boundaries.
3. Review retrieval relevance and citation quality.
4. Repeat evaluation after improvements using a new run label.

## Retrieval Improvement Experiment

Question: g014 — Reusing FastAPI dependencies

### Baseline: Top-K = 5

- Context size: 2,500 characters
- Relevant dependency-reuse chunk was not retrieved.
- Generated answer stated that documentation was insufficient.
- Golden-set scores: Accuracy 1, Groundedness 1, Format 1.

### Experiment: Top-K = 10

- Context size: 4,604 characters
- Context increased by 84.2%.
- Relevant chunk dependencies#8 appeared at rank 9.
- Generated answer correctly explained dependency reuse.
- The answer cited dependencies#8.
- No formal judge score was collected for this experiment.

### Findings

Increasing retrieval depth improved the answer for g014.
However, additional context may increase token usage and latency.

The default Top-K remains 5 to preserve the original baseline.
Further evaluation is needed before changing the default.

### Corpus Coverage Finding

Question g012 could not be answered from the retrieved context.

The downloaded query_parameters.md document did not contain
specific guidance for Query validation constraints such as
min_length, max_length, or pattern.

This suggests a corpus-coverage gap that should be addressed
by adding the relevant official FastAPI documentation.

## RAG Latency Measurement

### Test Configuration

- Endpoint: POST `/ask_batched`
- Question: What are path parameters in FastAPI?
- Retrieval depth: Top-K = 5
- Generation model: gpt-4o-mini
- Test requests: 1

### Results

| Metric | Result |
|---|---|
| HTTP status | 200 |
| End-to-end latency | 3.08 seconds |
| Retrieved sources | 5 |
| Reported generation cost | $0.00017535 |

### Findings

The RAG endpoint successfully completed retrieval and answer generation.

The measured latency includes the HTTP round trip, question embedding, retrieval, and generation.

The reported API cost covers chat generation only; embedding cost is excluded.

This is a preliminary single-request measurement. Multiple requests would be required to calculate average, p50, and p95 latency.