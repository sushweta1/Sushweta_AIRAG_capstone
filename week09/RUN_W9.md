# W9 Reference Package — Run Instructions

A working W9 reference: hybrid retrieval (BM25 + dense via RRF),
cross-encoder rerank, and optional query rewriting (HyDE / multi-query
/ step-back).

---

## Contents

```
W9_package/
├── src/
│   ├── _bootstrap.py            # Thread-limit env setup (carried from W7)
│   ├── ingest/                  # ENTIRE W8 module — unchanged
│   │   ├── parsers.py
│   │   ├── chunkers.py          # W8 hotfix applied (source in metadata)
│   │   ├── pii.py
│   │   ├── metadata.py
│   │   └── pipeline.py          # W8 hotfix applied (payload indexes)
│   └── rag/
│       ├── chunker.py           # W6/W7 sliding window (kept for ref)
│       ├── embeddings.py        # carried from W7
│       ├── qdrant_store.py      # carried from W8
│       ├── qdrant_rag.py        # EXTENDED — retrieval_method param
│       ├── retrieval.py         # NEW W9 — BM25 + RRF + rerank
│       └── query_rewrite.py     # NEW W9 — HyDE / multi-query / step-back
├── scripts/
│   ├── (all W8 scripts carried forward unchanged)
│   ├── compare_retrieval_methods.py  # NEW — Lab Step 1
│   ├── compute_precision_at_k.py     # NEW — Lab Step 2
│   └── try_query_rewrite.py          # NEW — Stretch Lab Step 4
├── data/
│   ├── corpus/                  # same 7 docs from W8
│   └── golden_set_full.jsonl    # same 20 questions
├── docs/
│   ├── adr/0001-capstone-framing.md   # extended with W9 section
│   └── kpi/wk9-snapshot-template.md   # W8 → W9 precision deltas
├── tests/test_w9.py             # 16 smoke tests
├── verify_w9.py                 # 40-step verifier
├── RUN_W9.sh
├── requirements.txt             # + rank-bm25 + sentence-transformers
└── .env.example
```

---

## Quick start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

Heavy install — sentence-transformers brings PyTorch (~500 MB). Allow
a few minutes. Once done, the first call to `rerank()` will also
download the cross-encoder model (~80 MB) to `~/.cache/huggingface`.

### 2. Set up Qdrant

Same as W8 — Cloud or local Docker. W9 does **not** re-ingest; it
uses the existing `capstone_chunks_v2` collection populated in W8.

```bash
# Make sure W8 collection is still populated:
python3 -c "
from src.rag.qdrant_store import _get_client, COLLECTION_NAME_V2
client = _get_client()
info = client.get_collection(COLLECTION_NAME_V2)
print(f'capstone_chunks_v2: {info.points_count} points')
"
```

If empty, re-run W8 ingestion before W9.

### 3. Run the verifier

```bash
bash RUN_W9.sh
```

Expected: 40 / 40 PASS.

---

## Running individual steps

### Lab Step 1 (Core) — Compare retrieval methods

```bash
python scripts/compare_retrieval_methods.py
```

Runs all 20 golden questions through dense, hybrid, and hybrid+rerank.
Writes `docs/wk9-retrieval-comparison.md` with per-question results.

### Lab Step 2 (Core) — Measure precision@k delta

```bash
python scripts/compute_precision_at_k.py
```

Computes precision@3 and precision@5 for each method, with deltas
against dense baseline. Writes `docs/wk9-precision-delta.md`.

### Lab Step 4 (Stretch) — Try one query rewriting technique

```bash
python scripts/try_query_rewrite.py --technique hyde
# or --technique multi_query
# or --technique step_back
```

Applies the chosen rewrite technique, compares precision@3 with vs
without. Writes `docs/wk9-query-rewrite-trial.md`.

### Run a single query with the new retrieval methods

```python
from src.rag.qdrant_store import load_store
from src.rag.qdrant_rag import ask_rag
from src.rag.retrieval import build_bm25_index, load_chunks_from_qdrant

store = load_store(embedding_model="text-embedding-3-small", dim=1536)
chunks = load_chunks_from_qdrant(store)
bm25 = build_bm25_index(chunks)

# W8-compat (dense, default)
r = ask_rag("What is the leave policy?", store)

# Hybrid (BM25 + dense via RRF)
r = ask_rag("What is the leave policy?", store,
            retrieval_method="hybrid",
            bm25_index=bm25, chunks=chunks)

# Hybrid + cross-encoder rerank
r = ask_rag("What is the leave policy?", store,
            retrieval_method="hybrid_rerank",
            bm25_index=bm25, chunks=chunks)

print(r["answer"])
print("Citations:")
for c in r["citations"]:
    print(f"  {c['source']} | {c['section_path']} | "
          f"score={c['score']:.3f} | "
          f"dense_rank={c['dense_rank']} bm25_rank={c['bm25_rank']}")
```

---

## What changed from W8

| Component | W8 | W9 |
|---|---|---|
| Retrieval methods | dense only | dense / hybrid / hybrid_rerank |
| `ask_rag()` | `(question, store, k, filter)` | `(question, store, k, filter, retrieval_method, bm25_index, chunks)` — backward compatible |
| BM25 | not used | rank-bm25, in-memory, rebuilt per session |
| Reranker | not used | local cross-encoder (ms-marco-MiniLM-L-6-v2) |
| Query rewriting | not used | HyDE / multi-query / step-back via OpenAI |
| Qdrant collection | `capstone_chunks_v2` | same — **no re-ingestion** |
| ADR 0001 | through W8 PII | extended with W9 retrieval section |

---

## Common issues

### "ImportError: No module named 'rank_bm25'"

```bash
pip install rank-bm25
```

### "Cross-encoder download failed — connection blocked"

The first call to `rerank()` downloads ~80 MB from HuggingFace. On
restricted networks (some Vocareum configs, corporate proxies):

```bash
# Pre-download with a known-working network:
python -c "
from sentence_transformers import CrossEncoder
CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
print('Downloaded.')
"

# Then run normally.
```

If download fails consistently, fall back to dense-only:
```python
ask_rag("...", store)   # default = dense; no cross-encoder needed
```

### "BM25 scores are all zero"

This happens when a query term appears in >50% of documents in your
corpus (IDF goes negative). On the 24-chunk W8 corpus, this affects
very common words like "leave" or "policy". Either:
- Use a more discriminating query (e.g., "cisco VPN" not "VPN")
- Increase corpus size (real production has 1000s of chunks)
- Switch to a different sparse retriever (BM25Plus, BM25L)

### "Hybrid retrieval slower than expected"

The hybrid pipeline does two retrievals (dense + BM25) in series.
For higher latency budgets, parallelise:

```python
import asyncio
# (out of scope for W9 — covered in W25 production hardening)
```

For now: ~30 ms dense + ~5 ms BM25 + ~170 ms rerank = ~205 ms total.

### "Latency p95 exceeds my budget"

Three knobs:
- Drop `top_k` for rerank from 3 to 1 if 1 chunk is enough
- Switch reranker from local to Cohere Rerank API (faster, paid)
- Skip rerank for "easy" queries (heuristic: queries with rare terms)

---

*W9 reference package. Advanced Retrieval per the official curriculum.*
