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

## (To be added in W9) — Advanced retrieval

*Reserved section — populated when learner completes W9 (Advanced
Retrieval — hybrid + rerank). The W8 metadata fields are designed
for the filter DSL we use in W9.*

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
