# ADR 0001 — Capstone Framing

**Status:** Living document — locks at M2 (W12 Design Review)
**Owner:** Capstone learner
**Created:** W5 (initial draft, locked v1)
**Last updated:** W8

> *Per the curriculum, ADR 0001 is the single accumulating decision
> record for the capstone's foundational technical choices. Every
> Phase 2 week (W6-W12) adds to it. At W12, it locks and becomes the
> reference for the M2 Design Review.*
>
> *Sections from earlier weeks remain — we extend, we don't rewrite.*

---

## Capstone use case (W5 — locked v1)

**Enterprise Knowledge Assistant (EKA).** An internal Q&A system over
a small policy corpus (HR + IT). Users type natural-language questions
and get cited answers grounded in the policies.

### Why this and not something else

- Tractable corpus size (5-20 documents at W6 baseline, scales to ~200 in production)
- Real failure modes — cross-document questions, vocabulary mismatch,
  edge cases — show up at this scale
- Pedagogically rich — every retrieval improvement we ship through
  W6-W11 has a measurable effect on this corpus

### Out of scope

- Multi-tenant isolation
- Multilingual support (English only)
- Personalisation (no per-user state)
- Real-time updates (corpus changes infrequently)

---

## Baseline numbers (W6 — first KPI snapshot)

| KPI | W6 value | Notes |
|---|---|---|
| Retrieval hit rate | __ / 20 | Top-3 retrieval against 20-question golden set |
| Cost per query | $______ | Embedding cost amortised; chat cost per call |
| Latency p50 | _____ms | Naive RAG in-process |
| Grounded response rate | N/A | Judged from W11 onwards |
| Task success rate | __ / 20 | Eyeball-graded at W6 |

---

## Vector stack (W7 — added)

### Embedding model

**Chosen:** _______________ (text-embedding-3-small / text-embedding-3-large)

**Reasoning:**
- Hit rate delta: ____ / 20 vs ____ / 20
- Justification: __________________________

### Vector store

**Chosen:** Qdrant

**Deployment mode:** _______________
- [ ] Qdrant Cloud (free tier, 1 GB cluster)
- [ ] Local Docker

### Similarity metric

**Chosen:** Cosine

### Index type

**Chosen:** HNSW (Qdrant default)

---

## Ingestion pipeline (W8 — added)

This is the W8 section. The capstone now ingests real document formats
through a structure-aware pipeline with PII scrubbing.

### Supported formats

**Chosen:** PDF · HTML · DOCX · Markdown · Plain text

- **PDF:** PyMuPDF (default). pdfplumber as a fallback for table-heavy documents.
- **HTML:** BeautifulSoup with `html.parser` backend.
- **DOCX:** python-docx (uses paragraph styles to detect headings).
- **Markdown:** built-in parser; splits on `#` headings.
- **Plain text:** no structure detection.

**Out of scope for W8:** OCR (scanned PDFs without text layer). The
pipeline detects this case and skips the document with a warning.
Adding OCR would require Tesseract + Pillow + significant time —
deferred until W28 if needed.

### Chunking strategy

**Chosen:** Structure-aware with paragraph-split fallback.

**Algorithm:**
1. If a parsed section fits within max_size (800 chars), emit it as one chunk.
2. If a section exceeds max_size, split by paragraph boundaries; accumulate paragraphs up to target_size (500 chars).
3. If a single paragraph exceeds max_size, fall back to sliding-window (W6's approach).

**Reasoning:**
- Eliminates mid-sentence cuts that W6's pure sliding window produced
- Each chunk carries its parent heading text — improves retrieval signal
- Cross-section bleed is eliminated; chunks don't span topic boundaries
- Sliding window is retained as last resort for genuinely long
  paragraphs (rare in policy corpora)

**Why not semantic chunking:** semantic chunking uses an LLM to find
topic boundaries. Doubles the build cost. The lift on our corpus
shape (HR / IT policy docs with clear sections) is marginal.

### Metadata schema (per chunk)

**Chosen:** 9 fields per chunk's Qdrant payload:

| Field | Type | Source |
|---|---|---|
| `source` | str | Filename |
| `doc_title` | str | First H1 / title element / first non-trivial PDF line |
| `doc_type` | str | "hr" / "it" / "general" (heuristic from name + path) |
| `section_path` | str | Heading hierarchy, e.g. "Leave > Annual Leave" |
| `heading` | str | The immediate parent heading |
| `heading_level` | int | 1 = h1, 2 = h2, etc. |
| `page` | int / None | Page number for PDFs; None otherwise |
| `ingested_at` | str | ISO 8601 timestamp |
| `has_pii` | bool | True if PII was detected and scrubbed |
| `pii_types` | list[str] | Types found, e.g. ["EMAIL", "PERSON"] |

**Reasoning:**
- These fields support the W9 filter-augmented retrieval work.
- doc_type taxonomy is deliberately simple; can refine in W14 if needed.
- `has_pii` lets us filter sensitive chunks out at query time when policy demands.

### PII handling

**Chosen:** Hybrid regex + Microsoft Presidio.

**Layers:**
1. **Regex baseline (always on):** catches emails, phone numbers,
   SSNs, UK NI numbers, credit cards. Deterministic, fast, no model
   download.
2. **Presidio upgrade (opt-in via `use_presidio=True`):** NER-based
   detection of names, addresses, organisations. Catches what regex
   can't. Requires spaCy model (~50MB) on first run.
3. **Manual audit (Lab Step 2):** sample 10 random chunks per
   ingestion run, eyeball-check for missed PII. Document gaps.

**Reasoning:**
- Neither regex nor Presidio alone is sufficient. Regex misses names;
  Presidio misses unusual ID formats and obfuscated PII.
- The audit step is the third leg — assumes both automated layers
  have gaps and surfaces them.

**Acknowledged gaps:**
- Presidio's NER is English-only by default. Non-Western names are
  often missed (Yuki Tanaka, Fatima Al-Rashid in our test corpus).
- Obfuscated emails (`person [at] domain [dot] com`) bypass the
  regex.
- The Lab Step 2 audit at sample size 10 finds high-frequency gaps
  but misses long-tail leaks.

### Data residency

**Chosen for capstone (W8 framing — full deep-dive at W28):**

| Data | Where it lives | Sent to OpenAI? |
|---|---|---|
| Source documents | `data/corpus/` (local / Vocareum) | No (parsing is local) |
| Chunk text + metadata | Qdrant (Cloud or local Docker) | No (only embeddings are computed via OpenAI) |
| Embeddings | OpenAI for computation, then stored in Qdrant | **Yes** — chunk text is sent to OpenAI for embedding |
| Queries | OpenAI for embedding + chat completion | **Yes** — every query text is sent to OpenAI |
| Conversations | Not persisted by the capstone | N/A |

**Implications:**
- If the capstone corpus contains genuine confidential data, OpenAI's
  data handling matters. The W8 default assumes synthetic / public
  test data; real production would require either OpenAI's enterprise
  privacy controls or a local embedding model.
- The PII scrubbing step is the safety net — even if chunks reach
  OpenAI, scrubbed text contains no individual identifiers.

**Deferred to W28:** full residency analysis (e.g. EU vs US data
flows, GDPR Article 5 alignment).

---

## Advanced retrieval (W9 — added)

This is the W9 section. The capstone's retrieval graduates from
pure-dense cosine to support hybrid and cross-encoder reranking as additional retrieval capabilities.

### Retrieval methods supported

`ask_rag` now accepts a `retrieval_method` parameter:

| Method | Description | When to use |
|---|---|---|
| `dense` (default) | W8 behaviour — Qdrant cosine | Fast queries, low-stakes corpora |
| `hybrid` | BM25 + dense fused via RRF | Mixed queries (exact + semantic) |
| `hybrid_rerank` | hybrid → top-20 candidates → cross-encoder → top-3 | Experimental; not the recommended default |

Backward compatibility: existing W8 callers using `ask_rag(question, store)`
continue to work — they get `retrieval_method='dense'`.

### BM25 implementation

**Library:** rank-bm25 (pure Python, ~3 KB import)
**Tokenizer:** lowercase alphanumeric regex (English HR/IT only — no
stemming, no language detection). Adequate for the curriculum corpus;
would need a proper tokenizer for multi-language production.
**Persistence:** in-memory, rebuilt per Python session (~30 seconds for
24 chunks). For production, persist via pickle and invalidate on
corpus changes.

### Hybrid combiner — RRF (Reciprocal Rank Fusion)

**Chosen:** RRF over weighted sum.

**Formula:** `rrf_score(doc) = Σ over retrievers of 1 / (rrf_k + rank)`

**rrf_k = 60** (canonical constant from Cormack et al. 2009).

**Why RRF over weighted sum:**
- No score-scale calibration needed (dense returns cosine ∈ [-1,1];
  BM25 returns unbounded positive scores — combining them by raw
  addition requires per-query normalisation)
- Rank position is a more stable signal than absolute score
- No magic α to tune

### Reranker

**Chosen:** Local cross-encoder via sentence-transformers.

**Model:** `cross-encoder/ms-marco-MiniLM-L-6-v2` (~80 MB,
downloads on first use).

**Why local over Cohere:**
- Free (no API costs, no key management)
- Reproducible (no rate limits, no API changes)
- Acceptable latency at lab scale (~200ms to rerank top-20)

**Latency cost:** Original estimate ~200ms. The W9 benchmark observed 441ms median retrieval latency for hybrid_rerank versus 34ms for dense, a pipeline-level difference of 407ms.

**Production alternative:** Cohere Rerank API offers ~50ms latency
at $1/1000 reranks. Switch if latency budget tightens; the
`rerank()` function in `src/rag/retrieval.py` is a clean swap point.

### Query rewriting (Stretch lab status)

Three techniques available in `src/rag/query_rewrite.py`:

- **HyDE** — draft hypothetical answer, embed THAT
- **Multi-Query** — generate 3 paraphrases, union retrievals
- **Step-Back** — generate more-general question, run BOTH

All three add one OpenAI call per query (~$0.0001 at gpt-4o-mini
rates). Capstone status: HyDE DROPPED from the default pipeline. Multi-Query and Step-Back passed functional verification but were not benchmarked for retrieval quality.

### Latency budget — end-to-end

Target: < 2 sec p50 for the capstone's user-facing query.

Approximate sub-budgets (measured on Vocareum + Qdrant Cloud):

| Stage | p50 budget |
|---|---|
| OpenAI embedding | ~80 ms |
| Qdrant dense retrieve | ~30 ms |
| BM25 retrieve | ~5 ms |
| RRF fusion | <1 ms |
| Cross-encoder rerank (top-20 → top-3) | ~170 ms |
| OpenAI chat completion | ~500 ms |
| **Total** | ~785 ms p50 |

The budgets above are reference estimates, not measured stage-level results from this experiment. Actual aggregate measurements are recorded in `docs/kpi/wk9-snapshot.md`.

### LlamaIndex — framework decision

**Not adopted this week.** A 15-line LlamaIndex equivalent was shown
in Topic 5 to demonstrate what the framework abstracts. Decision
to stay from-scratch for the capstone:

- Full visibility into the retrieval pipeline (no magic)
- No version-lock to LlamaIndex API churn
- W12 framework decision (M2 Design Review) will reconsider

---


### W9 experimental findings and final recommendation

**Status:** Benchmark completed; 40/40 verifier checks passed.

**Evaluation dataset:** 20 golden questions, 7 documents,
24 chunks in capstone_chunks_v2.

#### Experimental evidence

| Method | Hit rate | P@3 | P@5 | Retrieve p50 | E2E p50 |
|---|---:|---:|---:|---:|---:|
| Dense | 100% | 0.733 | 0.540 | 34ms | 1842ms |
| Hybrid | 100% | 0.700 | 0.540 | 34ms | 1619ms |
| Hybrid + Rerank | 100% | 0.667 | 0.480 | 441ms | 2154ms |

Retrieval latency is from the Precision@K experiment.
End-to-end latency is from the comparison experiment.

#### Decision 1 — Retain dense as default

Dense achieved the highest measured Precision@3 and
joint-highest Precision@5 with low retrieval latency.

Hybrid and hybrid_rerank remain supported options.

The original reference proposal to adopt hybrid_rerank
as the production default is superseded by this
benchmark-based recommendation.

No runtime default change is required because
ask_rag already defaults to dense.

#### Decision 2 — Retain RRF and local reranking

Retain RRF with rrf_k=60 and the local cross-encoder
ms-marco-MiniLM-L-6-v2 implementation.

Enable reranking selectively only when additional
evaluation demonstrates a measurable quality benefit.

#### Decision 3 — Drop HyDE from the default pipeline

HyDE was evaluated against hybrid_rerank.

- Baseline P@3: 0.667
- HyDE P@3: 0.550
- Delta: -0.117
- Improved: 1/20 questions
- Unchanged: 12/20 questions
- Deteriorated: 7/20 questions

Verdict: DROP.

Retain the implementation for future experimentation.
Multi-Query and Step-Back passed functional checks;
their quality impact remains unmeasured.

#### Decision 4 — Evaluation dataset integrity

Initial source hit rates were 45% for all methods.

Investigation identified outdated expected_source
filenames following multi-format ingestion.

Corrected 11 golden-set records:

- expense_policy.md -> expense_policy.pdf
- vpn_setup.md -> vpn_setup.html
- security_incident.md -> security_incident.docx

All methods subsequently achieved 100% source hit rate.

No changes were made to embeddings, chunking,
retrieval algorithms or Qdrant documents.

The filename correction assumes equivalent underlying
policy documents.

Future improvement: use stable document identifiers
and version evaluation datasets alongside the KB.

#### Decision 5 — Isolate verification artifacts

The verifier's three-question smoke evaluations
overwrote two full benchmark reports.

Full reports were backed up and restored.
All restored reports were verified against backups.

Future improvement: provide separate output paths
for smoke tests and full evaluation runs.

#### Decision 6 — Standardize environment configuration

Explicit python-dotenv loading was required for
standalone evaluation scripts.

Qdrant Cloud connectivity was restored after
reactivating the cluster.

Future improvement: declare python-dotenv as a
dependency and standardize configuration loading.

#### Decision 7 — Latency budget

Retain end-to-end p50 target below 2000ms.

Dense and hybrid met this target in the comparison.
Hybrid_rerank exceeded it by 154ms.

Verifier checks passed their thresholds but exceeded
the aspirational sub-second and sub-two-second targets.

Further optimization and repeated measurements
are required before production deployment.

#### Evaluation limitations

- Small corpus and golden set.
- Source-level relevance, not answer-bearing chunk relevance.
- Answer correctness and groundedness not measured here.
- Single-run latency observations.
- Recommendations are dataset-specific and provisional.

#### Supporting artifacts

- docs/kpi/wk9-snapshot.md
- docs/wk9-retrieval-comparison.md
- docs/wk9-precision-delta.md
- docs/wk9-query-rewrite-trial.md
- docs/experiments/wk9-retrieval-comparison-before-fix.md


---

## (To be added in W10) — Caching and KB lifecycle

*Reserved section.*

---

## (To be added in W11) — Eval framework

*Reserved section.*

---

## M2 lock target (W12)

By W12, all sections above are filled in and lock. At the M2 Design
Review, the learner defends each decision with the numbers from each
week's KPI snapshot. Post-W12, this ADR is read-only for the rest of
the programme — though new ADRs (0002 onwards) may be added for
agents/integration/observability.

---

*ADR 0001 lives in `docs/adr/0001-capstone-framing.md`. Update each
week. Commit each update.*
