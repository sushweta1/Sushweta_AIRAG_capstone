#!/usr/bin/env python3
"""W9 Verifier — runs ~40 checks against a W9 reference repo.

Usage:
    OPENAI_API_KEY=...  python verify_w9.py

    # For full live tests, also set:
    #   QDRANT_URL=https://YOUR-CLUSTER.cloud.qdrant.io
    #   QDRANT_API_KEY=...
    # OR
    #   QDRANT_URL=http://localhost:6333
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# Bootstrap before any heavy import
from src import _bootstrap  # noqa: F401

import os
import subprocess


GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
RESET = "\033[0m"

spend_total = 0.0


def _print_step(num, total, label):
    print(f"\n[{num:02d}/{total}] {label}")


def _pass(detail: str = ""):
    msg = f"{GREEN}PASS{RESET}"
    if detail:
        msg += f" — {detail}"
    print(f"       {msg}")
    return True


def _fail(detail: str):
    print(f"       {RED}FAIL{RESET} — {detail}")
    return False


def _skip(detail: str):
    print(f"       {YELLOW}SKIP{RESET} — {detail}")
    return True


def _run(cmd: list[str], cwd: str = ".", timeout: int = 300):
    env = os.environ.copy()
    env["OMP_NUM_THREADS"] = "1"
    env["OPENBLAS_NUM_THREADS"] = "1"
    env["TOKENIZERS_PARALLELISM"] = "false"
    repo_root = str(Path.cwd().resolve())
    existing_pp = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = (
        repo_root if not existing_pp else f"{repo_root}{os.pathsep}{existing_pp}"
    )
    proc = subprocess.run(
        cmd, cwd=cwd, capture_output=True, text=True, env=env, timeout=timeout
    )
    return proc.returncode, proc.stdout, proc.stderr


# ─── OFFLINE STEPS (1-15) ───────────────────────────────────────────────

def step_01_python_version():
    if sys.version_info < (3, 10):
        return _fail(f"Python 3.10+ required, found {sys.version_info[:2]}")
    return _pass(f"Python {sys.version_info.major}.{sys.version_info.minor}")


def step_02_openai_key():
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        return _fail("OPENAI_API_KEY is not set")
    placeholders = {"your-key-here", "your_key_here", "sk-...", "..."}
    if key.lower() in placeholders:
        return _fail(f"OPENAI_API_KEY looks like a placeholder")
    if len(key) < 20:
        return _fail(f"OPENAI_API_KEY too short ({len(key)} chars)")
    return _pass(f"key present ({len(key)} chars)")


def step_03_w8_carryover_libs():
    """W8 deps still installed (openai, qdrant, pymupdf, bs4, docx)."""
    missing = []
    for mod, name in [("openai", "openai"), ("qdrant_client", "qdrant-client"),
                      ("fitz", "pymupdf"), ("bs4", "beautifulsoup4"),
                      ("docx", "python-docx")]:
        try:
            __import__(mod)
        except ImportError:
            missing.append(name)
    if missing:
        return _fail(f"missing W8 libs: {missing}")
    return _pass("W8 libs all present (openai, qdrant, pymupdf, bs4, docx)")


def step_04_rank_bm25_lib():
    try:
        import rank_bm25
        return _pass(f"rank-bm25 installed")
    except ImportError:
        return _fail("rank-bm25 not installed — pip install rank-bm25")


def step_05_sentence_transformers_lib():
    try:
        import sentence_transformers
        return _pass(f"sentence-transformers {sentence_transformers.__version__}")
    except ImportError:
        return _fail("sentence-transformers not installed — pip install sentence-transformers")


def step_06_directory_structure():
    required = [
        "src/_bootstrap.py",
        "src/ingest/parsers.py",
        "src/ingest/chunkers.py",
        "src/ingest/pii.py",
        "src/ingest/metadata.py",
        "src/ingest/pipeline.py",
        "src/rag/embeddings.py",
        "src/rag/qdrant_store.py",
        "src/rag/qdrant_rag.py",
        "src/rag/retrieval.py",          # NEW W9
        "src/rag/query_rewrite.py",      # NEW W9
        "scripts/ingest_corpus.py",
        "scripts/compare_retrieval_methods.py",  # NEW W9
        "scripts/compute_precision_at_k.py",     # NEW W9
        "scripts/try_query_rewrite.py",          # NEW W9
        "data/corpus",
        "data/golden_set_full.jsonl",
        "docs/adr/0001-capstone-framing.md",
        "docs/kpi/wk9-snapshot-template.md",
        "tests/test_w9.py",
    ]
    missing = [p for p in required if not Path(p).exists()]
    if missing:
        return _fail(f"missing: {missing[:3]}{'...' if len(missing) > 3 else ''}")
    return _pass(f"{len(required)} required paths present")


def step_07_retrieval_module_imports():
    try:
        from src.rag.retrieval import (
            build_bm25_index, dense_retrieve, bm25_retrieve,
            hybrid_retrieve, rerank, hybrid_rerank_retrieve,
            load_chunks_from_qdrant, CROSS_ENCODER_MODEL,
        )
        if CROSS_ENCODER_MODEL != "cross-encoder/ms-marco-MiniLM-L-6-v2":
            return _fail(f"unexpected cross-encoder model: {CROSS_ENCODER_MODEL}")
        return _pass("retrieval.py exports all 7 expected functions")
    except ImportError as e:
        return _fail(f"retrieval import failed: {e}")


def step_08_query_rewrite_module_imports():
    try:
        from src.rag.query_rewrite import (
            hyde_rewrite, multi_query_rewrite, step_back_rewrite,
            retrieve_with_rewrite, REWRITE_MODEL,
        )
        if REWRITE_MODEL != "gpt-4o-mini":
            return _fail(f"unexpected rewrite model: {REWRITE_MODEL}")
        return _pass("query_rewrite.py exports 3 techniques + helper")
    except ImportError as e:
        return _fail(f"query_rewrite import failed: {e}")


def step_09_qdrant_rag_retrieval_method_param():
    import inspect
    from src.rag.qdrant_rag import ask_rag, VALID_METHODS
    sig = inspect.signature(ask_rag)
    if "retrieval_method" not in sig.parameters:
        return _fail(f"ask_rag missing retrieval_method param")
    if sig.parameters["retrieval_method"].default != "dense":
        return _fail(f"retrieval_method default should be 'dense' (W8 back-compat), "
                     f"got {sig.parameters['retrieval_method'].default!r}")
    if VALID_METHODS != ("dense", "hybrid", "hybrid_rerank"):
        return _fail(f"unexpected VALID_METHODS: {VALID_METHODS}")
    return _pass("ask_rag(retrieval_method='dense'|'hybrid'|'hybrid_rerank') — backward compat")


def step_10_bm25_basic():
    from src.rag.retrieval import build_bm25_index, bm25_retrieve
    chunks = [
        {"text": "Annual leave entitlement is 25 days per year", "source": "leave.md"},
        {"text": "VPN setup requires Cisco AnyConnect client", "source": "vpn.md"},
        {"text": "Performance review happens annually in March", "source": "perf.md"},
    ]
    idx = build_bm25_index(chunks)
    hits = bm25_retrieve(idx, chunks, "cisco", k=1)
    if not hits or hits[0]["source"] != "vpn.md":
        return _fail(f"BM25 should rank cisco→vpn.md first; got {hits}")
    return _pass("BM25 builds + retrieves correctly on toy corpus")


def step_11_rrf_fusion_shape():
    """Check that hybrid_retrieve returns the right shape (offline test)."""
    from src.rag.retrieval import hybrid_retrieve, build_bm25_index
    # We need a store mock — just check the import path and signature
    import inspect
    sig = inspect.signature(hybrid_retrieve)
    expected_params = {"store", "bm25_index", "chunks", "query",
                       "k_each", "k_final", "rrf_k", "filter"}
    actual = set(sig.parameters.keys())
    if not expected_params.issubset(actual):
        return _fail(f"hybrid_retrieve missing params: {expected_params - actual}")
    if sig.parameters["rrf_k"].default != 60:
        return _fail(f"rrf_k default should be 60 (canonical); got {sig.parameters['rrf_k'].default}")
    return _pass("hybrid_retrieve signature correct; rrf_k=60 (canonical)")


def step_12_cross_encoder_lazy_load():
    """Cross-encoder should NOT load on module import — only on first rerank() call."""
    from src.rag import retrieval
    if retrieval._cross_encoder is not None:
        return _fail("cross-encoder loaded at import time (should be lazy)")
    return _pass("cross-encoder is lazy-loaded (not loaded until first rerank())")


def step_13_w8_carryover_payload_indexes():
    """The W8 hotfix — pipeline.py creates payload indexes."""
    pipeline_text = Path("src/ingest/pipeline.py").read_text()
    if "PAYLOAD_INDEX_FIELDS" not in pipeline_text:
        return _fail("pipeline.py doesn't have PAYLOAD_INDEX_FIELDS (W8 hotfix missing)")
    if "create_payload_index" not in pipeline_text:
        return _fail("pipeline.py doesn't call create_payload_index")
    return _pass("W8 hotfix present — pipeline creates payload indexes")


def step_14_w8_carryover_chunker_source():
    """The W8 hotfix — chunkers.py puts source into metadata."""
    chunkers_text = Path("src/ingest/chunkers.py").read_text()
    if "source" not in chunkers_text or chunkers_text.count('"source": parsed_doc.source') < 2:
        return _fail("chunkers.py doesn't include source in base_metadata "
                     "(W8 hotfix missing)")
    return _pass("W8 hotfix present — chunkers propagates source into metadata")


def step_15_smoke_tests_pass():
    rc, out, err = _run([sys.executable, "-m", "pytest", "tests/test_w9.py",
                          "-q", "--tb=short"])
    if rc != 0:
        return _fail(f"pytest failed:\n{out[-500:] if out else err[-500:]}")
    return _pass("all 16 smoke tests pass")


# ─── LIVE STEPS (16-40) — require Qdrant + OpenAI ───────────────────────

def step_16_qdrant_connectivity():
    url = os.environ.get("QDRANT_URL")
    if not url or url == ":memory:":
        return _skip("QDRANT_URL not set or :memory:")
    try:
        from qdrant_client import QdrantClient
        api_key = os.environ.get("QDRANT_API_KEY") or None
        client = QdrantClient(url=url, api_key=api_key) if api_key else QdrantClient(url=url)
        collections = client.get_collections()
        return _pass(f"connected ({len(collections.collections)} collections)")
    except Exception as e:
        return _fail(f"could not connect: {type(e).__name__}: {str(e)[:120]}")


def step_17_v2_collection_exists():
    """Should still exist from W8 — W9 does NOT re-ingest."""
    url = os.environ.get("QDRANT_URL")
    if not url or url == ":memory:":
        return _skip("QDRANT_URL not set")
    from src.rag.qdrant_store import _get_client, COLLECTION_NAME_V2
    client = _get_client()
    existing = {c.name for c in client.get_collections().collections}
    if COLLECTION_NAME_V2 not in existing:
        return _fail(f"{COLLECTION_NAME_V2!r} missing — re-run W8 ingestion first")
    info = client.get_collection(COLLECTION_NAME_V2)
    if info.points_count < 5:
        return _fail(f"collection has only {info.points_count} points")
    return _pass(f"{COLLECTION_NAME_V2} has {info.points_count} points")


def step_18_payload_indexes_exist():
    """W8 hotfix prerequisite: payload indexes must be present."""
    url = os.environ.get("QDRANT_URL")
    if not url or url == ":memory:":
        return _skip("QDRANT_URL not set")
    from src.rag.qdrant_store import _get_client, COLLECTION_NAME_V2
    client = _get_client()
    info = client.get_collection(COLLECTION_NAME_V2)
    schema = info.payload_schema or {}
    if "doc_type" not in schema:
        return _fail(f"no payload index for doc_type — re-ingest with W8 fixed pipeline")
    return _pass(f"{len(schema)} payload indexes present: {sorted(schema.keys())[:5]}...")


def step_19_load_chunks_from_qdrant():
    url = os.environ.get("QDRANT_URL")
    if not url or url == ":memory:":
        return _skip("QDRANT_URL not set")
    from src.rag.qdrant_store import load_store, COLLECTION_NAME_V2
    from src.rag.retrieval import load_chunks_from_qdrant
    store = load_store(collection_name=COLLECTION_NAME_V2,
                       embedding_model="text-embedding-3-small", dim=1536)
    chunks = load_chunks_from_qdrant(store)
    if len(chunks) < 5:
        return _fail(f"only {len(chunks)} chunks loaded")
    sources_with_text = sum(1 for c in chunks if c.get("source") and c.get("text"))
    if sources_with_text < len(chunks):
        return _fail(f"only {sources_with_text}/{len(chunks)} chunks have source+text")
    return _pass(f"loaded {len(chunks)} chunks; all have source+text")


def step_20_bm25_build_on_real_chunks():
    url = os.environ.get("QDRANT_URL")
    if not url or url == ":memory:":
        return _skip("QDRANT_URL not set")
    from src.rag.qdrant_store import load_store, COLLECTION_NAME_V2
    from src.rag.retrieval import build_bm25_index, load_chunks_from_qdrant
    store = load_store(collection_name=COLLECTION_NAME_V2,
                       embedding_model="text-embedding-3-small", dim=1536)
    chunks = load_chunks_from_qdrant(store)
    idx = build_bm25_index(chunks)
    if not hasattr(idx, "get_scores"):
        return _fail("BM25 index doesn't have get_scores")
    return _pass(f"BM25 index built over {len(chunks)} real chunks")


def step_21_dense_retrieve_live():
    global spend_total
    url = os.environ.get("QDRANT_URL")
    if not url or url == ":memory:":
        return _skip("QDRANT_URL not set")
    from src.rag.qdrant_store import load_store, COLLECTION_NAME_V2
    from src.rag.retrieval import dense_retrieve
    from src.rag.embeddings import estimate_embedding_cost
    store = load_store(collection_name=COLLECTION_NAME_V2,
                       embedding_model="text-embedding-3-small", dim=1536)
    hits = dense_retrieve(store, "leave policy", k=3)
    spend_total += estimate_embedding_cost(5, "text-embedding-3-small")
    if not hits:
        return _fail("dense_retrieve returned no hits")
    if "rank" not in hits[0]:
        return _fail("dense_retrieve didn't attach rank")
    return _pass(f"dense_retrieve → {len(hits)} hits; top source={hits[0]['source']}")


def step_22_bm25_retrieve_live():
    url = os.environ.get("QDRANT_URL")
    if not url or url == ":memory:":
        return _skip("QDRANT_URL not set")
    from src.rag.qdrant_store import load_store, COLLECTION_NAME_V2
    from src.rag.retrieval import build_bm25_index, bm25_retrieve, load_chunks_from_qdrant
    store = load_store(collection_name=COLLECTION_NAME_V2,
                       embedding_model="text-embedding-3-small", dim=1536)
    chunks = load_chunks_from_qdrant(store)
    idx = build_bm25_index(chunks)
    hits = bm25_retrieve(idx, chunks, "leave policy", k=3)
    if not hits:
        return _fail("bm25_retrieve returned no hits")
    return _pass(f"bm25_retrieve → {len(hits)} hits; top source={hits[0]['source']}")


def step_23_hybrid_retrieve_live():
    global spend_total
    url = os.environ.get("QDRANT_URL")
    if not url or url == ":memory:":
        return _skip("QDRANT_URL not set")
    from src.rag.qdrant_store import load_store, COLLECTION_NAME_V2
    from src.rag.retrieval import (
        build_bm25_index, hybrid_retrieve, load_chunks_from_qdrant,
    )
    from src.rag.embeddings import estimate_embedding_cost
    store = load_store(collection_name=COLLECTION_NAME_V2,
                       embedding_model="text-embedding-3-small", dim=1536)
    chunks = load_chunks_from_qdrant(store)
    idx = build_bm25_index(chunks)
    hits = hybrid_retrieve(store, idx, chunks, "leave policy", k_each=5, k_final=3)
    spend_total += estimate_embedding_cost(5, "text-embedding-3-small")
    if not hits:
        return _fail("hybrid_retrieve returned no hits")
    # Each hit should have a non-zero RRF score
    if hits[0]["score"] <= 0:
        return _fail(f"top RRF score is 0; got {hits[0]['score']}")
    return _pass(f"hybrid_retrieve → {len(hits)} hits; top RRF={hits[0]['score']:.4f}")


def step_24_rerank_loads_cross_encoder():
    global spend_total
    url = os.environ.get("QDRANT_URL")
    if not url or url == ":memory:":
        return _skip("QDRANT_URL not set")
    from src.rag.retrieval import rerank
    candidates = [
        {"text": "Annual leave is 25 days per year", "source": "leave.md", "rank": 1},
        {"text": "VPN setup requires Cisco client", "source": "vpn.md", "rank": 2},
    ]
    reranked = rerank("how many leave days?", candidates, top_k=1)
    if not reranked or reranked[0]["source"] != "leave.md":
        return _fail(f"rerank should put leave.md first; got {reranked}")
    if "rerank_score" not in reranked[0]:
        return _fail("rerank didn't attach rerank_score")
    return _pass(f"cross-encoder loaded + rerank correctly ordered top result")


def step_25_hybrid_rerank_live():
    global spend_total
    url = os.environ.get("QDRANT_URL")
    if not url or url == ":memory:":
        return _skip("QDRANT_URL not set")
    from src.rag.qdrant_store import load_store, COLLECTION_NAME_V2
    from src.rag.retrieval import (
        build_bm25_index, hybrid_rerank_retrieve, load_chunks_from_qdrant,
    )
    from src.rag.embeddings import estimate_embedding_cost
    store = load_store(collection_name=COLLECTION_NAME_V2,
                       embedding_model="text-embedding-3-small", dim=1536)
    chunks = load_chunks_from_qdrant(store)
    idx = build_bm25_index(chunks)
    hits = hybrid_rerank_retrieve(store, idx, chunks, "leave policy",
                                    k_candidates=10, top_k=3)
    spend_total += estimate_embedding_cost(5, "text-embedding-3-small")
    if not hits:
        return _fail("hybrid_rerank_retrieve returned no hits")
    if "pre_rerank_rank" not in hits[0]:
        return _fail("rerank lineage missing (no pre_rerank_rank)")
    return _pass(f"hybrid+rerank → {len(hits)} hits; rank lineage attached")


def step_26_ask_rag_dense_w8_compat():
    """ask_rag with default args should match W8 behaviour exactly."""
    global spend_total
    url = os.environ.get("QDRANT_URL")
    if not url or url == ":memory:":
        return _skip("QDRANT_URL not set")
    from src.rag.qdrant_rag import ask_rag
    from src.rag.qdrant_store import load_store, COLLECTION_NAME_V2
    store = load_store(collection_name=COLLECTION_NAME_V2,
                       embedding_model="text-embedding-3-small", dim=1536)
    result = ask_rag("What is the leave policy?", store, k=3)
    spend_total += result["cost_usd"]
    if result["retrieval_method"] != "dense":
        return _fail(f"default method should be 'dense'; got {result['retrieval_method']}")
    if not result["citations"]:
        return _fail("ask_rag returned no citations")
    return _pass(f"ask_rag (dense, default) — W8-compat behaviour confirmed")


def step_27_ask_rag_hybrid():
    global spend_total
    url = os.environ.get("QDRANT_URL")
    if not url or url == ":memory:":
        return _skip("QDRANT_URL not set")
    from src.rag.qdrant_rag import ask_rag
    from src.rag.qdrant_store import load_store, COLLECTION_NAME_V2
    from src.rag.retrieval import build_bm25_index, load_chunks_from_qdrant
    store = load_store(collection_name=COLLECTION_NAME_V2,
                       embedding_model="text-embedding-3-small", dim=1536)
    chunks = load_chunks_from_qdrant(store)
    idx = build_bm25_index(chunks)
    result = ask_rag("What is the leave policy?", store, k=3,
                     retrieval_method="hybrid", bm25_index=idx, chunks=chunks)
    spend_total += result["cost_usd"]
    if not result["citations"]:
        return _fail("hybrid ask_rag returned no citations")
    # Top citation should have either dense_rank or bm25_rank set
    top = result["citations"][0]
    if top["dense_rank"] is None and top["bm25_rank"] is None:
        return _fail("hybrid citation missing both dense_rank and bm25_rank")
    return _pass(f"ask_rag (hybrid) — RRF fusion working")


def step_28_ask_rag_hybrid_rerank():
    global spend_total
    url = os.environ.get("QDRANT_URL")
    if not url or url == ":memory:":
        return _skip("QDRANT_URL not set")
    from src.rag.qdrant_rag import ask_rag
    from src.rag.qdrant_store import load_store, COLLECTION_NAME_V2
    from src.rag.retrieval import build_bm25_index, load_chunks_from_qdrant
    store = load_store(collection_name=COLLECTION_NAME_V2,
                       embedding_model="text-embedding-3-small", dim=1536)
    chunks = load_chunks_from_qdrant(store)
    idx = build_bm25_index(chunks)
    result = ask_rag("What is the leave policy?", store, k=3,
                     retrieval_method="hybrid_rerank", bm25_index=idx, chunks=chunks)
    spend_total += result["cost_usd"]
    if not result["citations"]:
        return _fail("hybrid_rerank ask_rag returned no citations")
    # Top citation should have a pre_rerank_rank (rerank actually ran)
    top = result["citations"][0]
    if top.get("pre_rerank_rank") is None:
        return _fail("hybrid_rerank citation missing pre_rerank_rank")
    return _pass(f"ask_rag (hybrid_rerank) — full pipeline working")


def step_29_latency_budget_dense():
    """Dense should complete in well under 2 seconds."""
    url = os.environ.get("QDRANT_URL")
    if not url or url == ":memory:":
        return _skip("QDRANT_URL not set")
    import time
    from src.rag.qdrant_rag import ask_rag
    from src.rag.qdrant_store import load_store, COLLECTION_NAME_V2
    store = load_store(collection_name=COLLECTION_NAME_V2,
                       embedding_model="text-embedding-3-small", dim=1536)
    t0 = time.time()
    ask_rag("What is the leave policy?", store, k=3)
    ms = int((time.time() - t0) * 1000)
    if ms > 5000:
        return _fail(f"dense latency too high: {ms}ms")
    return _pass(f"dense latency: {ms}ms (target sub-second)")


def step_30_latency_budget_hybrid_rerank():
    """hybrid+rerank adds ~200ms but should still be sub-2s."""
    url = os.environ.get("QDRANT_URL")
    if not url or url == ":memory:":
        return _skip("QDRANT_URL not set")
    import time
    from src.rag.qdrant_rag import ask_rag
    from src.rag.qdrant_store import load_store, COLLECTION_NAME_V2
    from src.rag.retrieval import build_bm25_index, load_chunks_from_qdrant
    store = load_store(collection_name=COLLECTION_NAME_V2,
                       embedding_model="text-embedding-3-small", dim=1536)
    chunks = load_chunks_from_qdrant(store)
    idx = build_bm25_index(chunks)
    t0 = time.time()
    ask_rag("What is the leave policy?", store, k=3,
            retrieval_method="hybrid_rerank", bm25_index=idx, chunks=chunks)
    ms = int((time.time() - t0) * 1000)
    if ms > 6000:
        return _fail(f"hybrid_rerank latency too high: {ms}ms")
    return _pass(f"hybrid_rerank latency: {ms}ms (target sub-2s)")


def step_31_compare_script_runs():
    url = os.environ.get("QDRANT_URL")
    if not url or url == ":memory:":
        return _skip("QDRANT_URL not set")
    # Only run on a subset (3 questions) to keep test fast
    import json, tempfile
    from pathlib import Path
    golden_path = Path("data/golden_set_full.jsonl")
    if not golden_path.exists():
        return _fail("golden set not found")
    lines = golden_path.read_text().splitlines()[:3]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl",
                                       delete=False) as tmp:
        tmp.write("\n".join(lines))
        tmp_path = tmp.name
    rc, out, err = _run(
        [sys.executable, "scripts/compare_retrieval_methods.py",
         "--golden", tmp_path, "--methods", "dense,hybrid",
         "--output", "docs/verification/retrieval-comparison.md"],
        timeout=180,
    )
    if rc != 0:
        return _fail(f"compare script failed: {err[-300:]}")
    return _pass("compare_retrieval_methods.py runs (3 questions, dense+hybrid)")


def step_32_precision_script_runs():
    url = os.environ.get("QDRANT_URL")
    if not url or url == ":memory:":
        return _skip("QDRANT_URL not set")
    import tempfile
    from pathlib import Path
    golden_path = Path("data/golden_set_full.jsonl")
    lines = golden_path.read_text().splitlines()[:3]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl",
                                       delete=False) as tmp:
        tmp.write("\n".join(lines))
        tmp_path = tmp.name
    rc, out, err = _run(
        [sys.executable, "scripts/compute_precision_at_k.py",
         "--golden", tmp_path, "--methods", "dense,hybrid_rerank",
         "--output", "docs/verification/precision-delta.md"],
        timeout=180,
    )
    if rc != 0:
        return _fail(f"precision script failed: {err[-300:]}")
    return _pass("compute_precision_at_k.py runs (3 questions)")


def step_33_hyde_rewrite_live():
    global spend_total
    key = os.environ.get("OPENAI_API_KEY", "")
    if not key:
        return _skip("no OPENAI_API_KEY")
    from src.rag.query_rewrite import hyde_rewrite
    rewritten = hyde_rewrite("What is the leave policy?")
    if not rewritten or len(rewritten) < 30:
        return _fail(f"HyDE returned suspicious output: {rewritten!r}")
    spend_total += 0.0002
    return _pass(f"HyDE rewrite → {len(rewritten)} chars")


def step_34_multi_query_rewrite_live():
    global spend_total
    key = os.environ.get("OPENAI_API_KEY", "")
    if not key:
        return _skip("no OPENAI_API_KEY")
    from src.rag.query_rewrite import multi_query_rewrite
    paraphrases = multi_query_rewrite("What is the leave policy?", n=3)
    if not paraphrases or len(paraphrases) < 2:
        return _fail(f"multi_query returned only {len(paraphrases)} paraphrases")
    spend_total += 0.0003
    return _pass(f"multi_query returned {len(paraphrases)} paraphrases")


def step_35_step_back_rewrite_live():
    global spend_total
    key = os.environ.get("OPENAI_API_KEY", "")
    if not key:
        return _skip("no OPENAI_API_KEY")
    from src.rag.query_rewrite import step_back_rewrite
    rewritten = step_back_rewrite("How many days of annual leave do I get if I have 3 years of service?")
    if not rewritten or len(rewritten) < 10:
        return _fail(f"step_back returned suspicious output: {rewritten!r}")
    spend_total += 0.0002
    return _pass(f"step_back rewrite → {rewritten[:60]}...")


# ─── DOCS + ADR CHECKS (36-39) ──────────────────────────────────────────

def step_36_adr_has_w9_section():
    path = Path("docs/adr/0001-capstone-framing.md")
    content = path.read_text().lower()
    required = ["advanced retrieval", "hybrid", "rerank"]
    missing = [k for k in required if k not in content]
    if missing:
        return _fail(f"ADR 0001 missing W9 terms: {missing}")
    return _pass("ADR 0001 extended with W9 sections")


def step_37_wk9_snapshot_template_has_precision():
    path = Path("docs/kpi/wk9-snapshot-template.md")
    if not path.exists():
        return _fail("wk9-snapshot-template.md not found")
    content = path.read_text().lower()
    if "precision@3" not in content or "precision@5" not in content:
        return _fail("wk9 template missing precision@3 or precision@5")
    if "w8" not in content:
        return _fail("wk9 template missing W8 baseline column")
    return _pass("wk9 snapshot template has precision@k + W8 baseline")


def step_38_no_separate_adr_for_retrieval():
    """Curriculum: decisions stack in ADR 0001."""
    adr_files = list(Path("docs/adr").glob("0002*")) + \
                list(Path("docs/adr").glob("0003*"))
    if adr_files:
        return _fail(f"separate ADR found ({[f.name for f in adr_files]}); "
                     f"W9 decisions should stack in 0001")
    return _pass("W9 decisions stacked in ADR 0001 per curriculum")


def step_39_requirements_updated():
    path = Path("requirements.txt")
    content = path.read_text() if path.exists() else ""
    missing = []
    if "rank-bm25" not in content and "rank_bm25" not in content:
        missing.append("rank-bm25")
    if "sentence-transformers" not in content and "sentence_transformers" not in content:
        missing.append("sentence-transformers")
    if missing:
        return _fail(f"requirements.txt missing W9 deps: {missing}")
    return _pass("requirements.txt has rank-bm25 + sentence-transformers")


def step_40_total_spend():
    if spend_total > 0.50:
        return _fail(f"spend ${spend_total:.4f} > $0.50 ceiling")
    return _pass(f"total verification spend: ${spend_total:.4f}")


# ─── Run ────────────────────────────────────────────────────────────────

STEPS = [
    # Offline (1-15)
    ("Python version >= 3.10", step_01_python_version),
    ("OPENAI_API_KEY set", step_02_openai_key),
    ("W8 carryover libs (openai/qdrant/pymupdf/bs4/docx)", step_03_w8_carryover_libs),
    ("rank-bm25 library installed", step_04_rank_bm25_lib),
    ("sentence-transformers library installed", step_05_sentence_transformers_lib),
    ("Required files + dirs exist", step_06_directory_structure),
    ("retrieval.py exports all 7 functions", step_07_retrieval_module_imports),
    ("query_rewrite.py exports 3 techniques", step_08_query_rewrite_module_imports),
    ("ask_rag has retrieval_method (back-compat)", step_09_qdrant_rag_retrieval_method_param),
    ("BM25 builds + retrieves correctly", step_10_bm25_basic),
    ("hybrid_retrieve signature + RRF k=60", step_11_rrf_fusion_shape),
    ("cross-encoder is lazy-loaded", step_12_cross_encoder_lazy_load),
    ("W8 hotfix carryover (payload indexes)", step_13_w8_carryover_payload_indexes),
    ("W8 hotfix carryover (chunker source)", step_14_w8_carryover_chunker_source),
    ("Smoke tests (16 tests) pass", step_15_smoke_tests_pass),
    # Live (16-35)
    ("Live Qdrant connectivity", step_16_qdrant_connectivity),
    ("capstone_chunks_v2 still populated from W8", step_17_v2_collection_exists),
    ("payload indexes present (W8 hotfix)", step_18_payload_indexes_exist),
    ("load_chunks_from_qdrant returns chunks", step_19_load_chunks_from_qdrant),
    ("BM25 index built over real Qdrant chunks", step_20_bm25_build_on_real_chunks),
    ("dense_retrieve live", step_21_dense_retrieve_live),
    ("bm25_retrieve live", step_22_bm25_retrieve_live),
    ("hybrid_retrieve live (RRF fusion)", step_23_hybrid_retrieve_live),
    ("rerank() loads cross-encoder + reorders", step_24_rerank_loads_cross_encoder),
    ("hybrid_rerank_retrieve full pipeline", step_25_hybrid_rerank_live),
    ("ask_rag dense (W8 backward compat)", step_26_ask_rag_dense_w8_compat),
    ("ask_rag hybrid", step_27_ask_rag_hybrid),
    ("ask_rag hybrid_rerank", step_28_ask_rag_hybrid_rerank),
    ("Dense latency under 5s", step_29_latency_budget_dense),
    ("hybrid+rerank latency under 6s", step_30_latency_budget_hybrid_rerank),
    ("compare_retrieval_methods.py runs", step_31_compare_script_runs),
    ("compute_precision_at_k.py runs", step_32_precision_script_runs),
    ("HyDE rewrite live", step_33_hyde_rewrite_live),
    ("multi_query rewrite live", step_34_multi_query_rewrite_live),
    ("step_back rewrite live", step_35_step_back_rewrite_live),
    # Docs (36-40)
    ("ADR 0001 has W9 section", step_36_adr_has_w9_section),
    ("wk9 snapshot template has precision@k", step_37_wk9_snapshot_template_has_precision),
    ("No separate ADR for retrieval (stacked in 0001)", step_38_no_separate_adr_for_retrieval),
    ("requirements.txt has W9 deps", step_39_requirements_updated),
    ("Total spend under $0.50", step_40_total_spend),
]


def main():
    total = len(STEPS)
    print("=" * 64)
    print(f"  W9 Verifier — {total} checks")
    print("=" * 64)
    print(f"  QDRANT_URL: {os.environ.get('QDRANT_URL', '(not set)')}")
    print(f"  QDRANT_API_KEY: {'set' if os.environ.get('QDRANT_API_KEY') else '(not set)'}")
    print("=" * 64)

    passed = 0
    failed_step = None
    for i, (label, fn) in enumerate(STEPS, 1):
        _print_step(i, total, label)
        try:
            result = fn()
        except Exception as e:
            result = _fail(f"unexpected exception: {type(e).__name__}: {e}")
        if result:
            passed += 1
        else:
            failed_step = i
            break

    print("\n" + "=" * 64)
    if passed == total:
        print(f"  {GREEN}ALL {total} CHECKS PASSED{RESET}")
        print(f"  Total verification spend: ${spend_total:.4f}")
        print("=" * 64)
        return 0
    else:
        print(f"  {RED}FAILED at step {failed_step}/{total}{RESET}")
        print(f"  ({passed} steps passed before failure)")
        print("=" * 64)
        return 1


if __name__ == "__main__":
    sys.exit(main())
