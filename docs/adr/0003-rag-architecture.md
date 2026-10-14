# ADR 0003: Retrieval-Augmented Generation Architecture

## Status

Accepted as the Week 6 baseline, with improvements identified.

## Context

The existing FastAPI Knowledge Assistant generates answers using
an LLM without retrieving relevant documentation first.

Week 6 introduces Retrieval-Augmented Generation (RAG) to
ground answers in a local FastAPI documentation corpus.

The goal is to improve factual grounding while preserving
the existing public API contract.

## Decision

Implement a simple retrieval-augmented generation pipeline.

### Ingestion and Indexing

- Use official FastAPI Markdown documentation as the corpus.
- Split documents into 500-character chunks with 50-character overlap.
- Generate embeddings using text-embedding-3-small.
- Store embeddings and chunk metadata in data/embeddings.json.
- The initial index contains 303 chunks with 1536-dimensional vectors.

### Retrieval

- Embed each incoming user question.
- Compare its embedding against indexed chunks using cosine similarity.
- Retrieve the five highest-ranked chunks by default.
- Use brute-force similarity search for this small corpus.

### Generation

- Supply retrieved documentation chunks as context to gpt-4o-mini.
- Instruct the model to answer using the supplied documentation.
- Return the generated answer and retrieved source identifiers.

### API Integration

- Integrate RAG into POST /ask_batched.
- Preserve the existing Answer response schema.
- Preserve SQLite answer persistence.
- Keep POST /ask and GET /health unchanged.

## Evaluation

The existing 20-question golden set was used to compare
Week 5 and Week 6.

| Metric | Week 5 | Week 6 |
|---|---:|---:|
| Accuracy | 3.60 | 3.05 |
| Groundedness | 3.80 | 3.15 |
| Format | 3.75 | 3.30 |
| Overall average | 3.72 | 3.17 |

Scores use a four-point judge scale.

The Week 6 baseline scored lower across all three metrics.
Therefore, introducing RAG did not automatically improve
measured answer quality.

The existing judge evaluates groundedness against ideal
answers rather than directly against retrieved source chunks.
This limits how strongly the groundedness scores can be
interpreted as evidence of document grounding.

## Retrieval Investigation

Two low-scoring questions were investigated.

### g012: Query Parameter Validation

The retrieved documentation did not contain sufficient
information about FastAPI Query validation constraints.

The downloaded query_parameters.md file did not include
min_length, max_length, pattern, or Query( examples.

This indicates a documentation coverage gap.

### g014: Dependency Reuse

The relevant information existed in the indexed corpus,
but was not selected among the top five retrieved chunks.

The relevant dependencies#8 chunk appeared at rank 9.

Increasing Top-K from 5 to 10 produced a useful answer
that cited dependencies#8.

Retrieved context increased from 2500 to 4604 characters,
an increase of approximately 84.2%.

This was a single-question experiment, not a complete
golden-set re-evaluation.

## Trade-offs

Advantages:

- Answers can reference retrieved documentation.
- The existing API contract remains stable.
- JSON-based indexing is simple to inspect and reproduce.
- Brute-force retrieval is sufficient for the initial corpus.

Limitations:

- Relevant chunks may fall outside the default Top-K.
- Missing documents cannot be recovered by retrieval.
- Fixed-character chunking may split important explanations.
- Larger Top-K values increase context size and may
  increase generation cost and latency.
- JSON-based brute-force retrieval may not scale efficiently.
- Embedding costs are not included in the current
  chat-only API cost calculation.

## Consequences

The Week 6 RAG baseline is functional and evaluated,
but its measured answer quality is below Week 5.

The default Top-K remains 5 to preserve the evaluated baseline.

Future improvements should include:

- Adding missing official FastAPI documentation.
- Improving chunk boundaries and document preparation.
- Testing retrieval depth and ranking strategies.
- Measuring end-to-end latency and embedding costs.
- Re-running the full golden set after improvements.

The detailed results are recorded in
docs/kpi/wk6-snapshot.md.
