# KPI Snapshot — W9 — Advanced Retrieval

**Capstone:** Enterprise Knowledge Assistant (EKA)
**Collection:** capstone_chunks_v2
**Corpus:** 7 documents, 24 chunks
**Golden set:** 20 questions
**Verification:** 40/40 PASS
**Recommended retrieval method:** dense
**W9 experimental method:** hybrid_rerank

> The dense baseline was measured during W9 using the
> unchanged W8 collection and corrected golden set.
> It is not a historical W8 measurement.

---

## Executive Summary

All three retrieval methods achieved a 100% source hit
rate after correcting outdated golden-set references.

Dense retrieval achieved the highest Precision@3,
while hybrid retrieval matched dense Precision@5.

Cross-encoder reranking reduced measured precision
and introduced substantial retrieval latency.

HyDE query rewriting reduced Precision@3 further.
The experimental verdict is DROP.

Recommendation: retain dense retrieval as the default
and preserve advanced retrieval methods for future
experimentation.

---

## The 8 standard KPIs

| KPI | Dense baseline | W9 hybrid_rerank | Delta | Notes |
|---|---|---|---|---|
| Task success rate | Not measured | Not measured | N/A | Requires answer grading |
| Grounded response rate | Not measured | Not measured | N/A | W11 evaluation |
| Hallucination rate | Not measured | Not measured | N/A | W11 evaluation |
| Retrieval hit rate | 20/20 | 20/20 | 0 pp | Source-level hit |
| Tool success rate | N/A | N/A | N/A | Future milestone |
| Cost / query | $0.000076 | $0.000077 | +$0.000001 | Reported comparison cost / 20 |
| Latency p50 / p95 | 1842/2702ms | 2154/8362ms | +312/+5660ms | End-to-end |
| Escalation rate | N/A | N/A | N/A | Future milestone |

---

## W9 headline metrics

| Metric | Dense baseline | Hybrid + Rerank | Delta |
|---|---:|---:|---:|
| Precision@3 | 0.733 | 0.667 | -0.066 |
| Precision@5 | 0.540 | 0.480 | -0.060 |
| MRR | Not measured | Not measured | N/A |
| Retrieve latency p50 | 34ms | 441ms | +407ms |
| Retrieve latency p95 | 39ms | 728ms | +689ms |

Precision and retrieval latency are from the
dedicated Precision@K experiment.

---

## Retrieval method breakdown

| Method | Hit rate | P@3 | P@5 | Retrieve p50 | Retrieve p95 | E2E p50 | E2E p95 | Cost / 20 q |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Dense | 100% | 0.733 | 0.540 | 34ms | 39ms | 1842ms | 2702ms | $0.00152 |
| Hybrid | 100% | 0.700 | 0.540 | 34ms | 36ms | 1619ms | 2229ms | $0.00152 |
| Hybrid + Rerank | 100% | 0.667 | 0.480 | 441ms | 728ms | 2154ms | 8362ms | $0.00154 |

Retrieval latency is from the precision experiment.
End-to-end latency and cost are from the comparison
experiment.

---

## What moved and why

- Dense achieved the highest measured Precision@3.
- Hybrid reduced P@3 by 3.3 percentage points and
  matched dense P@5.
- Reranking reduced P@3 by 6.6 percentage points and
  P@5 by 6 percentage points.
- Reranking increased median retrieval latency by
  approximately 13x compared with dense retrieval.
- Hybrid achieved the lowest observed E2E latency.
  Repeated benchmarks are needed to establish stability.
- Possible contributing factors include the small
  corpus, overlapping policy terminology and the
  source-level relevance definition.
- These contributing factors remain hypotheses.

---

## Latency budget

| Stage | p50 | p95 |
|---|---|---|
| Query embedding | Not separately measured | Not separately measured |
| BM25 retrieval | Not separately measured | Not separately measured |
| Dense retrieval | Not separately isolated | Not separately isolated |
| RRF fusion | Not separately measured | Not separately measured |
| Cross-encoder rerank | Not separately measured | Not separately measured |
| LLM generation | Not separately measured | Not separately measured |
| Dense end-to-end | 1842ms | 2702ms |
| Hybrid end-to-end | 1619ms | 2229ms |
| Hybrid + Rerank end-to-end | 2154ms | 8362ms |

Target: end-to-end p50 below 2 seconds.

Dense and hybrid met this target in the comparison.
Hybrid + Rerank exceeded the target by 154ms.

---

## Per-question precision@3

| Q | Question | Expected | P@3 dense | P@3 hybrid | P@3 hybrid_rerank |
|---|---|---|---|---|---|
| q01 | How many days of paid annual leave do I get? | leave_policy.md | 0.67 | 0.67 | 1.00 |
| q02 | Can I carry over unused leave to next year? | leave_policy.md | 0.67 | 0.67 | 0.67 |
| q03 | How much parental leave is available? | leave_policy.md | 0.33 | 0.33 | 0.33 |
| q04 | Do I need a doctor's note for sick leave? | leave_policy.md | 0.67 | 0.67 | 0.67 |
| q05 | How many days per week can I work from home? | wfh_policy.md | 1.00 | 0.67 | 0.33 |
| q06 | Can I expense a co-working space membership? | wfh_policy.md | 0.33 | 0.33 | 0.67 |
| q07 | What's the home office equipment allowance? | wfh_policy.md | 0.67 | 1.00 | 0.67 |
| q08 | What are the core hours when working remotely? | wfh_policy.md | 1.00 | 0.33 | 0.67 |
| q09 | What's the meal allowance during US business trave | expense_policy.pdf | 0.67 | 0.67 | 0.33 |
| q10 | How long do I have to submit travel receipts? | expense_policy.pdf | 0.67 | 0.67 | 0.67 |
| q11 | Can I expense a Notion subscription for myself? | expense_policy.pdf | 0.67 | 0.67 | 0.67 |
| q12 | Is there a cap on training expenses? | expense_policy.pdf | 0.67 | 0.67 | 0.67 |
| q13 | How do I reset my VPN password? | vpn_setup.html | 1.00 | 1.00 | 1.00 |
| q14 | What's the IT helpdesk number? | vpn_setup.html | 0.67 | 1.00 | 0.67 |
| q15 | Is the VPN available on mobile devices? | vpn_setup.html | 1.00 | 1.00 | 1.00 |
| q16 | What do I do if my laptop is stolen at the airport | security_incident.docx | 1.00 | 1.00 | 1.00 |
| q17 | What's the security hotline number for urgent out- | security_incident.docx | 1.00 | 0.67 | 0.67 |
| q18 | Will I be punished for reporting a phishing click  | security_incident.docx | 1.00 | 0.67 | 1.00 |
| q19 | How long does it take to get a replacement laptop? | security_incident.docx | 0.33 | 0.67 | 0.33 |
| q20 | Do I need to use the VPN when working from home? | wfh_policy.md | 0.67 | 0.67 | 0.33 |

---

## Stretch lab — HyDE query rewriting

- Technique: Hypothetical Document Embeddings (HyDE)
- Baseline: Hybrid + Rerank
- Baseline P@3: 0.667
- HyDE P@3: 0.550
- Delta: -0.117
- Improved questions: 1/20
- Unchanged questions: 12/20
- Deteriorated questions: 7/20
- Verdict: DROP

Detailed results:
docs/wk9-query-rewrite-trial.md

---

## Engineering finding 1 — Evaluation dataset drift

Initial retrieval hit rate was 45% for all methods.

Root cause: outdated expected_source filenames
following multi-format ingestion.

Corrected references:

| Original | Corrected | Questions |
|---|---|---:|
| expense_policy.md | expense_policy.pdf | 4 |
| vpn_setup.md | vpn_setup.html | 3 |
| security_incident.md | security_incident.docx | 4 |

After correcting 11 golden-set references, all
three methods achieved 100% source hit rate.

No retrieval algorithms, embeddings or Qdrant
documents were changed during this correction.

The original golden set and before-fix report
were preserved.

The filename alignment assumes corresponding files
represent the same underlying policies.

---

## Engineering finding 2 — Verifier output isolation

The verifier runs three-question smoke evaluations
that modified the full benchmark reports.

The original 20-question reports were backed up
before verification and restored afterward.

All three restored experiment reports were verified
against their backups.

Recommendation: use separate output paths for
smoke tests and full benchmark reports.

---

## Engineering finding 3 — Environment configuration

The standalone evaluation scripts required explicit
loading of .env before importing retrieval modules.

A python-dotenv wrapper was used successfully.

The Qdrant Cloud cluster also required reactivation
before connectivity could be restored.

Recommendation: standardize environment loading
and declare python-dotenv as a dependency.

---

## Verification

- Technical checks: 40/40 PASS
- Smoke tests: 16/16 PASS
- Failed checks: 0
- Skipped checks: 0
- Verification spend: $0.0011
- Verification budget: $0.50
- Budget utilization: 0.22%

Verifier latency checks:

| Method | Observed | Pass threshold | Aspirational target |
|---|---:|---:|---:|
| Dense | 3166ms | 5000ms | 1000ms |
| Hybrid + Rerank | 4380ms | 6000ms | 2000ms |

Both checks passed their verification thresholds
but missed their aspirational targets.

---

## Decisions and next steps

- Recommended default: dense retrieval.
- Retain hybrid retrieval as an optional method.
- Retain cross-encoder reranking for experimentation.
- Hybrid combiner: RRF with rrf_k=60.
- Reranker: cross-encoder/ms-marco-MiniLM-L-6-v2.
- Query rewriting: DROP HyDE from the default pipeline.
- Target E2E p50: below 2000ms.
- Record the experimental decisions in ADR 0001.
- W10: caching and knowledge-base lifecycle.
- W11: groundedness, answer relevance and RAG evaluation.

---

## Spend tracking

| Activity | Reported spend |
|---|---:|
| Dense comparison | $0.00152 |
| Hybrid comparison | $0.00152 |
| Hybrid + Rerank comparison | $0.00154 |
| Corrected comparison subtotal | $0.00458 |
| Initial comparison before correction | $0.00456 |
| Verification | $0.00110 |
| Known spend subtotal | $0.01024 |
| Precision experiment | Not recorded |
| HyDE experiment | Not recorded |
| Total W9 spend | Not fully measured |
| Cumulative W6-W9 spend | Not available |

Phase budget: $5.
Full phase-budget compliance cannot be established
without the missing spend records.

---

## Evaluation limitations

- Small corpus: 24 chunks across 7 documents.
- Golden set: 20 questions.
- Relevance is based on source filename rather than
  answer-bearing chunk content.
- A 100% source hit rate does not establish answer
  correctness or groundedness.
- Latency observations are from individual runs.
- Recommendations are provisional and dataset-specific.
