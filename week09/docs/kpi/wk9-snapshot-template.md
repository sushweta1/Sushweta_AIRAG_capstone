# KPI Snapshot — W9 — Advanced Retrieval

> *W8 → W9 delta. The headline numbers this week are precision@3 and
> precision@5 — hit rate alone is too coarse when small golden sets
> meet noisier retrieval methods.*

**Capstone:** Enterprise Knowledge Assistant (EKA)
**Collection:** capstone_chunks_v2 (unchanged from W8)
**Retrieval method (W9):** hybrid_rerank
**Retrieval method (W8 baseline):** dense

---

## The 8 standard KPIs

| KPI | W8 value | W9 value | Δ | Notes |
|---|---|---|---|---|
| Task success rate | __ / 20 | __ / 20 | __ | Eyeball-graded |
| Grounded response rate | N/A | __ / 20 | __ | First LLM-judge run from W11 |
| Hallucination rate | N/A | N/A | — | Inverse of grounded |
| Retrieval hit rate | __ / 20 | __ / 20 | __ | Top-3 contains expected source |
| Tool success rate | N/A | N/A | — | Tools at M3 (W18) |
| Cost / query | $______ | $______ | __ | Chat cost per query |
| Latency p50 / p95 | __ms / __ms | __ms / __ms | __ | hybrid+rerank adds ~200ms |
| Escalation rate | N/A | N/A | — | Added at M3 |

---

## W9 headline metrics (NEW this week)

| Metric | W8 (dense) | W9 (hybrid+rerank) | Δ |
|---|---|---|---|
| **Precision@3** | __ | __ | __ |
| **Precision@5** | __ | __ | __ |
| MRR | __ | __ | __ |
| Retrieve latency p50 | __ms | __ms | __ms |
| Retrieve latency p95 | __ms | __ms | __ms |

*Headlines from `docs/wk9-precision-delta.md`. Paste here.*

---

## Retrieval method breakdown

Three methods compared on the same 20-question golden set:

| Method | P@3 | P@5 | Retrieve p50 | E2E p50 | Cost / 20 q |
|---|---|---|---|---|---|
| dense (W8 baseline) | __ | __ | __ms | __ms | $__ |
| hybrid (BM25 + dense via RRF) | __ | __ | __ms | __ms | $__ |
| hybrid + cross-encoder rerank | __ | __ | __ms | __ms | $__ |

---

## What moved + why

> *2-3 specific observations comparing W8 → W9.*

- Precision@3 moved __% because: __________
- Where hybrid won: __________ (e.g., exact-term queries)
- Where reranker won: __________ (e.g., ambiguous queries that benefit from re-scoring)
- Where neither helped: __________ (corpus gap? question quality?)

---

## Latency budget

| Stage | p50 latency | p95 latency |
|---|---|---|
| Query embedding (OpenAI) | __ms | __ms |
| BM25 retrieve | __ms | __ms |
| Dense retrieve (Qdrant) | __ms | __ms |
| RRF fusion | __ms | __ms |
| Cross-encoder rerank (top-20 → top-3) | __ms | __ms |
| LLM generation | __ms | __ms |
| **End-to-end** | __ms | __ms |

Target: end-to-end < 2 sec p50 for the capstone. Reality from this week: ____.

---

## Per-question diff (paste from `docs/wk9-precision-delta.md`)

> Table of all 20 questions with P@3 for each method.

---

## Stretch lab — query rewriting trial (optional)

If you did the Stretch lab:

- Technique tried: HyDE / Multi-Query / Step-Back
- Verdict: KEEP / DROP / MARGINAL
- Per-question delta in `docs/wk9-query-rewrite-trial.md`

---

## Decisions / next steps

> *What did this week's KPIs tell you? What changes in W10?*

- ADR 0001 extended with W9 "Advanced retrieval" section
  - Hybrid combiner = RRF (rrf_k=60)
  - Reranker = local cross-encoder/ms-marco-MiniLM-L-6-v2
  - Latency budget: ~__ms end-to-end p50
  - Query rewriting: ____ (kept / dropped / not tried)
- W10 preview: caching strategy will reduce repeated-query cost; KB lifecycle for when corpus updates

---

## Spend tracking

- W9 lab spend (this week): $______
  - 60 golden-set runs across 3 methods: $______
  - 20 query rewrite runs (if Stretch done): $______
  - 1 compute_kpis run: $______
- Cumulative phase spend (W6 + W7 + W8 + W9): $______
- Within phase budget ($5 ceiling for Phase 2 lab work): ✓ / ✗
