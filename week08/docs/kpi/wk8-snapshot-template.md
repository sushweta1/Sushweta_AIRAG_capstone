# KPI Snapshot — W8 — Document Ingestion + PII Awareness

> *Same 8-KPI format used since W6. Diffs vs W7 show whether the new
> ingestion pipeline (structure-aware chunking + metadata + PII scrub)
> actually moved any KPI that matters.*

**Capstone:** Enterprise Knowledge Assistant (EKA)
**Collection (W8):** capstone_chunks_v2
**Collection (W7 baseline):** capstone_chunks
**Embedding model:** _______________

---

## The 8 KPIs

| KPI | W7 value | W8 value | Δ | Notes |
|---|---|---|---|---|
| Task success rate | __ / 20 | __ / 20 | __ | Eyeball-graded; LLM-judge from W11 |
| Grounded response rate | N/A | N/A | — | Judged from W11 |
| Hallucination rate | N/A | N/A | — | Inverse of grounded |
| Retrieval hit rate | __ / 20 | __ / 20 | __ | Top-3 against golden set |
| Tool success rate | N/A | N/A | — | Tools at M3 (W18) |
| Cost / query | $______ | $______ | __ | Chat cost per query |
| Latency p50 / p95 | __ms / __ms | __ms / __ms | __ | End-to-end |
| Escalation rate | N/A | N/A | — | Added at M3 |

---

## Ingestion-specific metrics (new this week)

| Metric | Value | Notes |
|---|---|---|
| Documents processed | __ / __ | Total in corpus / successfully ingested |
| Documents skipped | __ | Scanned PDFs, unsupported formats, parse errors |
| Total chunks (W8 v2) | __ | Compare to W7's __ chunks |
| Mean chunk size (chars) | __ | Target was 500 |
| Chunks with PII detected | __ / __ (___%) | Higher = scrubber working harder |
| PII types found | [____, ____, ____] | E.g. EMAIL, PHONE, PERSON |
| Audit residual count (10-sample) | __ | Chunks where audit_pii.py flagged residual PII |

---

## Top observations

> *Write 2-3 specific observations comparing W7 → W8.*

- Structure-aware chunking impact: __________
- Metadata enrichment impact (specifically, where citations now include section_path + page): __________
- PII scrubbing — what got caught, what got missed: __________

---

## Per-question diff vs W7

> *(Auto-generated from scripts/compare_v1_vs_v2.py — paste the
> per-question table from docs/experiments/wk8-v1-vs-v2.md here.)*

---

## Decisions / next steps

> *What did this week's KPIs tell you? What changes in W9?*

- ADR 0001 updated with ingestion + chunking + metadata + PII + residency sections
- W9 preview: ____________________

---

## Spend tracking

- W8 lab spend (this week): $______
  - Ingestion (embeddings for 7 docs): $______
  - Comparison eval (40 questions across two collections): $______
- Cumulative phase spend (W6 + W7 + W8): $______
- Within phase budget ($2 ceiling for Phase 2 lab work): ✓ / ✗
