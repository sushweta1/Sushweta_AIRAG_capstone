# W8 Reference Package — Run Instructions

A working W8 reference: real document parsing (PDF/HTML/DOCX/Markdown),
structure-aware chunking, metadata enrichment, PII scrubbing,
end-to-end ingestion into Qdrant.

---

## Contents

```
W8_package/
├── src/
│   ├── _bootstrap.py            # Thread-limit env setup (carried from W7)
│   ├── ingest/                  # NEW W8 package
│   │   ├── parsers.py           # PDF / HTML / DOCX / MD dispatch
│   │   ├── chunkers.py          # Structure-aware chunker
│   │   ├── pii.py               # Regex + Presidio (optional)
│   │   ├── metadata.py          # 9-field schema + helpers
│   │   └── pipeline.py          # End-to-end orchestration (~120 lines)
│   └── rag/
│       ├── chunker.py           # W6/W7 sliding window — kept for comparison
│       ├── embeddings.py        # carried from W7
│       ├── qdrant_store.py      # EXTENDED with filter helpers
│       └── qdrant_rag.py        # EXTENDED with optional filter param
├── scripts/
│   ├── ingest_corpus.py         # Lab Step 1 — full pipeline
│   ├── audit_pii.py             # Lab Step 2 — sample chunks for PII review
│   ├── compare_v1_vs_v2.py      # Lab Step 3 helper — W7 vs W8 collections
│   ├── run_rag_eval.py          # Defaults to capstone_chunks_v2 now
│   ├── compute_kpis.py          # unchanged from W7
│   ├── build_index.py           # unchanged from W7
│   └── migrate_to_qdrant.py     # W7-baseline collection (for compare)
├── data/
│   ├── corpus/                  # 7 sample docs: 3 md + 2 pdf + 1 html + 1 docx
│   └── golden_set_full.jsonl    # carried from W7 (20 questions)
├── docs/
│   ├── adr/0001-capstone-framing.md   # extended with W8 sections
│   └── kpi/wk8-snapshot-template.md   # W7→W8 delta column
├── tests/test_w8.py             # Smoke tests (no API, no Qdrant)
├── verify_w8.py                 # 35-step verifier
├── RUN_W8.sh
├── requirements.txt
└── .env.example
```

---

## Quick start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

Presidio is commented out in `requirements.txt` — uncomment to enable
the NER upgrade for PII detection. Regex baseline always works.

### 2. Set up Qdrant

Same as W7 — Cloud or local Docker. Set env vars:

```bash
# Qdrant Cloud
export QDRANT_URL=https://YOUR-CLUSTER.cloud.qdrant.io
export QDRANT_API_KEY=...

# OR local Docker
export QDRANT_URL=http://localhost:6333
```

And your OpenAI key:

```bash
export OPENAI_API_KEY=sk-...
```

### 3. Run the verifier

```bash
bash RUN_W8.sh
```

Expected: 35 / 35 PASS (live steps SKIP if QDRANT_URL not set).

---

## Running individual steps

### Lab Step 1 — Re-ingest the corpus with the new pipeline

```bash
# Regex-only PII (the baseline)
python scripts/ingest_corpus.py

# With Presidio (after uncommenting in requirements.txt + pip install)
python scripts/ingest_corpus.py --use-presidio
```

This produces `capstone_chunks_v2` with the full metadata payload.

### Lab Step 2 — Audit PII scrubbing

```bash
python scripts/audit_pii.py --n 10
```

Samples 10 random chunks, flags any with residual PII patterns.
Eyeball-check the output. Run with `--n 20` for stronger sampling.

### Lab Step 3 — Compare W7 vs W8 collections

Requires BOTH collections to exist (run W7's `migrate_to_qdrant.py`
first if you haven't):

```bash
python scripts/compare_v1_vs_v2.py
```

Writes `docs/experiments/wk8-v1-vs-v2.md` with per-question hit deltas.

### Run a single query with a metadata filter

```python
from src.rag.qdrant_store import load_store, eq
from src.rag.qdrant_rag import ask_rag

store = load_store(embedding_model="text-embedding-3-small", dim=1536)

# Unfiltered (W7-equivalent)
result = ask_rag("What is the leave policy?", store)

# With filter — only search HR docs
result = ask_rag("What is the leave policy?", store, filter=eq("doc_type", "hr"))
print(result["answer"])
print("Citations:")
for c in result["citations"]:
    print(f"  - {c['source']} | {c['section_path']} | p.{c['page']}")
```

---

## What changed from W7

| Component | W7 | W8 |
|---|---|---|
| Corpus formats | Markdown only | PDF + HTML + DOCX + Markdown + text |
| Chunker | Sliding window (sliced mid-sentence) | Structure-aware (heading-respecting) |
| Chunk metadata | `{text, source, embedding_model}` | 9-field schema with section_path, page, has_pii, etc. |
| Qdrant collection | `capstone_chunks` | `capstone_chunks_v2` (kept alongside for comparison) |
| `qdrant_store.retrieve()` | No filter support | Optional `filter=Filter(...)` parameter |
| `ask_rag()` | `(question, store, k)` | `(question, store, k, filter=None)` — backward compatible |
| PII handling | None | Regex baseline + Presidio upgrade |
| ADR 0001 | Through W7 vector stack | Through W8 ingestion + PII + residency |

---

## Common issues

### "ImportError: No module named 'fitz'"

PyMuPDF isn't installed. Run `pip install pymupdf`.

### "ImportError: No module named 'presidio_analyzer'"

Presidio isn't installed. Either uncomment in `requirements.txt`
and `pip install -r requirements.txt`, or stick with regex-only PII
(the default — works fine without Presidio).

### "Collection capstone_chunks_v2 doesn't exist"

Run `python scripts/ingest_corpus.py` first.

### "Mismatched vector dimension"

Built the collection with one embedding model, querying with another.
Pass `--model text-embedding-3-large` consistently across
ingest_corpus + ask_rag.

### "PII audit found residual matches in ingested chunks"

Expected, sometimes. The hybrid PII approach has gaps:
- Obfuscated emails (e.g. `alice [at] example [dot] com`) bypass regex
- Non-Western names bypass Presidio's English NER
- Custom ID formats (e.g. internal employee IDs) bypass both

Document the gaps in your wk8-snapshot. That's the audit story — not
a failure.

---

*W8 reference package. Document Ingestion + PII Awareness per the
official curriculum.*
