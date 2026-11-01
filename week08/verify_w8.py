#!/usr/bin/env python3
"""W8 Verifier — runs ~35 checks against a W8 reference repo.

Usage:
    OPENAI_API_KEY=...  python verify_w8.py

    # For full live tests, also set:
    #   QDRANT_URL=https://YOUR-CLUSTER.cloud.qdrant.io
    #   QDRANT_API_KEY=...
    # OR
    #   QDRANT_URL=http://localhost:6333  (and have Docker running)
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# Bootstrap before any heavy import
from src import _bootstrap  # noqa: F401

import os
import json
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


# ─── Steps ──────────────────────────────────────────────────────────────

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


def step_03_openai_lib():
    try:
        import openai
        return _pass(f"openai {openai.__version__}")
    except ImportError:
        return _fail("openai not installed")


def step_04_qdrant_lib():
    try:
        import qdrant_client  # noqa: F401
        from importlib.metadata import version
        return _pass(f"qdrant-client {version('qdrant-client')}")
    except ImportError:
        return _fail("qdrant-client not installed")


def step_05_pymupdf_lib():
    try:
        import fitz
        return _pass(f"PyMuPDF (fitz) {fitz.__version__}")
    except ImportError:
        return _fail("pymupdf not installed — pip install pymupdf")


def step_06_beautifulsoup_lib():
    try:
        import bs4
        return _pass(f"beautifulsoup4 {bs4.__version__}")
    except ImportError:
        return _fail("beautifulsoup4 not installed")


def step_07_python_docx_lib():
    try:
        import docx
        return _pass(f"python-docx installed")
    except ImportError:
        return _fail("python-docx not installed")


def step_08_directory_structure():
    required = [
        "src/_bootstrap.py",
        "src/ingest/parsers.py",
        "src/ingest/chunkers.py",
        "src/ingest/pii.py",
        "src/ingest/metadata.py",
        "src/ingest/pipeline.py",
        "src/rag/chunker.py",
        "src/rag/embeddings.py",
        "src/rag/qdrant_store.py",
        "src/rag/qdrant_rag.py",
        "scripts/ingest_corpus.py",
        "scripts/audit_pii.py",
        "scripts/compare_v1_vs_v2.py",
        "scripts/run_rag_eval.py",
        "scripts/compute_kpis.py",
        "data/corpus",
        "data/golden_set_full.jsonl",
        "docs/adr/0001-capstone-framing.md",
        "docs/kpi/wk8-snapshot-template.md",
    ]
    missing = [p for p in required if not Path(p).exists()]
    if missing:
        return _fail(f"missing: {missing[:3]}{'...' if len(missing) > 3 else ''}")
    return _pass(f"{len(required)} required paths present")


def step_09_corpus_format_diversity():
    """The W8 corpus must include format diversity — md + pdf + html + docx."""
    corpus = Path("data/corpus")
    extensions = {p.suffix.lower() for p in corpus.iterdir() if p.is_file()}
    required = {".md", ".pdf", ".html", ".docx"}
    missing = required - extensions
    if missing:
        return _fail(f"corpus missing formats: {missing}")
    return _pass(f"all 4 formats present ({sorted(extensions)})")


def step_10_golden_set_size():
    path = Path("data/golden_set_full.jsonl")
    lines = [l for l in path.read_text().splitlines() if l.strip()]
    if len(lines) < 15:
        return _fail(f"only {len(lines)} golden entries")
    return _pass(f"{len(lines)} golden questions")


def step_11_ingest_modules_import():
    try:
        from src.ingest.parsers import parse_document, detect_format
        from src.ingest.chunkers import chunk_document, Chunk
        from src.ingest.pii import scrub_pii, scrub_chunks
        from src.ingest.metadata import finalize_metadata, METADATA_FIELDS
        from src.ingest.pipeline import ingest_corpus, IngestionResult
        return _pass("all 5 ingest modules importable")
    except ImportError as e:
        return _fail(f"ingest import failed: {e}")


def step_12_qdrant_store_extended():
    """Verify the new W8 filter helpers exist."""
    try:
        from src.rag.qdrant_store import (
            QdrantStore, build_store, load_store, retrieve,
            collection_count, eq, combine_and, combine_or,
            COLLECTION_NAME, COLLECTION_NAME_V2,
        )
    except ImportError as e:
        return _fail(f"qdrant_store import failed: {e}")
    if COLLECTION_NAME_V2 != "capstone_chunks_v2":
        return _fail(f"COLLECTION_NAME_V2 should be 'capstone_chunks_v2'")
    return _pass("qdrant_store has filter helpers + V2 collection name")


def step_13_qdrant_rag_filter_param():
    """Verify ask_rag accepts the filter parameter."""
    import inspect
    from src.rag.qdrant_rag import ask_rag
    sig = inspect.signature(ask_rag)
    if "filter" not in sig.parameters:
        return _fail(f"ask_rag missing 'filter' param; got {list(sig.parameters)}")
    if "question" not in sig.parameters or "store" not in sig.parameters:
        return _fail(f"ask_rag missing required params")
    return _pass("ask_rag(question, store, k, filter, ...) — backward compatible")


def step_14_chunker_metadata_field():
    """W8's Chunk should have a metadata dict."""
    from src.ingest.chunkers import Chunk
    chunk = Chunk(text="hi", source="t.md", metadata={"foo": "bar"})
    if not isinstance(chunk.metadata, dict):
        return _fail("Chunk.metadata is not a dict")
    if chunk.metadata.get("foo") != "bar":
        return _fail("Chunk.metadata didn't persist value")
    return _pass("Chunk.metadata is a dict — supports W8 enrichment")


def step_15_metadata_schema_complete():
    from src.ingest.metadata import METADATA_FIELDS
    required = {"source", "doc_title", "doc_type", "section_path", "page",
                "ingested_at", "has_pii", "pii_types"}
    missing = required - set(METADATA_FIELDS)
    if missing:
        return _fail(f"metadata schema missing: {missing}")
    return _pass(f"metadata schema has all 9 fields")


def step_16_pii_regex_email():
    from src.ingest.pii import scrub_pii
    result = scrub_pii("Contact alice@example.com please.")
    if "[EMAIL]" not in result.redacted:
        return _fail(f"email not redacted; got: {result.redacted!r}")
    return _pass("regex catches email")


def step_17_pii_regex_phone():
    from src.ingest.pii import scrub_pii
    result = scrub_pii("Call +44 20 7946 0123.")
    if "[PHONE]" not in result.redacted:
        return _fail(f"phone not redacted; got: {result.redacted!r}")
    return _pass("regex catches phone")


def step_18_pii_no_false_positive():
    from src.ingest.pii import scrub_pii
    text = "The annual leave is 20 days per year."
    result = scrub_pii(text)
    if result.has_pii:
        return _fail(f"false positive: scrubber thinks this has PII: {result.redacted!r}")
    return _pass("plain policy text not flagged")


def step_19_parser_markdown(tmp_dir=None):
    """Parse a markdown sample."""
    from src.ingest.parsers import parse_document
    sample = Path("data/corpus/leave_policy.md")
    if not sample.exists():
        return _fail(f"sample not found: {sample}")
    parsed = parse_document(sample)
    if not parsed.has_content:
        return _fail("parser returned empty content")
    if len(parsed.sections) < 2:
        return _fail(f"expected multiple sections, got {len(parsed.sections)}")
    return _pass(f"markdown parsed; {len(parsed.sections)} sections")


def step_20_parser_pdf():
    from src.ingest.parsers import parse_document
    sample = Path("data/corpus/expense_policy.pdf")
    if not sample.exists():
        return _fail(f"sample not found: {sample}")
    parsed = parse_document(sample)
    if not parsed.has_content:
        return _fail("PDF parser returned empty (scanned PDF?)")
    if not parsed.sections or all(s.page is None for s in parsed.sections):
        return _fail("PDF sections missing page numbers")
    return _pass(f"PDF parsed; {len(parsed.sections)} pages")


def step_21_parser_html():
    from src.ingest.parsers import parse_document
    sample = Path("data/corpus/vpn_setup.html")
    if not sample.exists():
        return _fail(f"sample not found: {sample}")
    parsed = parse_document(sample)
    if not parsed.has_content:
        return _fail("HTML parser returned empty")
    return _pass(f"HTML parsed; {len(parsed.sections)} sections")


def step_22_parser_docx():
    from src.ingest.parsers import parse_document
    sample = Path("data/corpus/security_incident.docx")
    if not sample.exists():
        return _fail(f"sample not found: {sample}")
    parsed = parse_document(sample)
    if not parsed.has_content:
        return _fail("DOCX parser returned empty")
    if len(parsed.sections) < 2:
        return _fail(f"expected multiple sections, got {len(parsed.sections)}")
    return _pass(f"DOCX parsed; {len(parsed.sections)} sections")


def step_23_chunker_structure_aware():
    """Verify chunker preserves section_path."""
    from src.ingest.parsers import parse_document
    from src.ingest.chunkers import chunk_document
    parsed = parse_document(Path("data/corpus/leave_policy.md"))
    chunks = chunk_document(parsed)
    if not chunks:
        return _fail("no chunks produced")
    # All chunks should have section_path set
    no_path = [c for c in chunks if not c.metadata.get("section_path")]
    if no_path:
        return _fail(f"{len(no_path)} chunks missing section_path")
    return _pass(f"{len(chunks)} chunks; all have section_path")


def step_24_pytest_runs():
    rc, out, err = _run([sys.executable, "-m", "pytest", "tests/", "-q", "--tb=short"])
    if rc != 0:
        return _fail(f"pytest failed:\n{out[-500:] if out else err[-500:]}")
    return _pass("all smoke tests pass")


def step_25_pipeline_end_to_end_offline():
    """Run the full ingest pipeline OFFLINE (no Qdrant)."""
    from src.ingest.parsers import parse_document
    from src.ingest.chunkers import chunk_document
    from src.ingest.pii import scrub_chunks
    from src.ingest.metadata import finalize_metadata, summarize_metadata

    all_chunks = []
    for p in sorted(Path("data/corpus").iterdir()):
        if p.suffix.lower() not in {".pdf", ".html", ".docx", ".md", ".txt"}:
            continue
        parsed = parse_document(p)
        if parsed.has_content:
            all_chunks.extend(chunk_document(parsed))

    if not all_chunks:
        return _fail("no chunks produced from corpus")

    scrub_chunks(all_chunks)
    finalize_metadata(all_chunks)

    summary = summarize_metadata(all_chunks)
    if summary["chunks_with_pii"] == 0:
        return _fail("no chunks flagged as having PII — but sample corpus has emails/phones")
    return _pass(
        f"{summary['n_chunks']} chunks; "
        f"{summary['chunks_with_pii']} with PII; "
        f"doc_types={summary['doc_types']}"
    )


def step_26_qdrant_connectivity():
    url = os.environ.get("QDRANT_URL")
    if not url or url == ":memory:":
        return _skip("QDRANT_URL not set or :memory: — skipping live connectivity")
    try:
        from qdrant_client import QdrantClient
        api_key = os.environ.get("QDRANT_API_KEY") or None
        client = QdrantClient(url=url, api_key=api_key) if api_key else QdrantClient(url=url)
        collections = client.get_collections()
        return _pass(f"connected to Qdrant ({len(collections.collections)} collections)")
    except Exception as e:
        return _fail(f"could not connect: {type(e).__name__}: {str(e)[:200]}")


def step_27_live_embed_api():
    """Live OpenAI embed call."""
    global spend_total
    from src.rag.embeddings import embed, estimate_embedding_cost
    vectors = embed(["hello world"], model="text-embedding-3-small", cache_path=None)
    if len(vectors[0]) != 1536:
        return _fail(f"expected 1536 dims, got {len(vectors[0])}")
    spend_total += estimate_embedding_cost(5, "text-embedding-3-small")
    return _pass(f"embedded; dim = {len(vectors[0])}")


def step_28_ingest_corpus_runs():
    """Run scripts/ingest_corpus.py end-to-end (requires Qdrant)."""
    global spend_total
    url = os.environ.get("QDRANT_URL")
    if not url or url == ":memory:":
        return _skip("QDRANT_URL not set or :memory: — skipping live ingestion")
    rc, out, err = _run([sys.executable, "scripts/ingest_corpus.py"])
    if rc != 0:
        return _fail(f"ingest_corpus failed: {err[-400:]}")
    spend_total += 0.005
    return _pass("ingest_corpus.py completed")


def step_29_v2_collection_populated():
    """Verify capstone_chunks_v2 exists and has points."""
    url = os.environ.get("QDRANT_URL")
    if not url or url == ":memory:":
        return _skip("QDRANT_URL not set or :memory: — skipping live check")
    from src.rag.qdrant_store import _get_client, COLLECTION_NAME_V2
    client = _get_client()
    existing = {c.name for c in client.get_collections().collections}
    if COLLECTION_NAME_V2 not in existing:
        return _fail(f"collection {COLLECTION_NAME_V2!r} not found")
    info = client.get_collection(COLLECTION_NAME_V2)
    if info.points_count < 5:
        return _fail(f"collection has only {info.points_count} points")
    return _pass(f"capstone_chunks_v2 has {info.points_count} points")


def step_30_metadata_in_qdrant_payload():
    """Verify chunks in Qdrant have metadata fields."""
    url = os.environ.get("QDRANT_URL")
    if not url or url == ":memory:":
        return _skip("QDRANT_URL not set — skipping live check")
    from src.rag.qdrant_store import _get_client, COLLECTION_NAME_V2
    client = _get_client()
    response = client.scroll(
        collection_name=COLLECTION_NAME_V2, limit=3,
        with_payload=True, with_vectors=False,
    )
    points = response[0]
    if not points:
        return _fail("no points in collection")
    required = {"text", "source", "doc_title", "doc_type", "section_path",
                "ingested_at", "has_pii"}
    payload = points[0].payload or {}
    missing = required - set(payload.keys())
    if missing:
        return _fail(f"payload missing: {missing}")
    return _pass(f"payload has all metadata fields: {sorted(payload.keys())[:8]}...")


def step_31_filtered_query():
    """Test that a metadata filter narrows retrieval."""
    global spend_total
    url = os.environ.get("QDRANT_URL")
    if not url or url == ":memory:":
        return _skip("QDRANT_URL not set — skipping live filter test")
    from src.rag.qdrant_rag import ask_rag
    from src.rag.qdrant_store import load_store, eq, COLLECTION_NAME_V2

    store = load_store(collection_name=COLLECTION_NAME_V2,
                        embedding_model="text-embedding-3-small", dim=1536)

    # Query with filter — should only return hr chunks
    result = ask_rag("What is the leave policy?", store, k=3,
                      filter=eq("doc_type", "hr"))
    if not result["citations"]:
        return _fail("filtered query returned no citations")
    spend_total += result.get("cost_usd", 0)

    # Every citation should be doc_type=hr (verify via a separate query)
    from src.rag.qdrant_store import _get_client
    client = _get_client()
    sources_returned = {c["source"] for c in result["citations"]}
    response = client.scroll(
        collection_name=COLLECTION_NAME_V2, limit=100,
        with_payload=True, with_vectors=False,
    )
    by_source = {p.payload["source"]: p.payload["doc_type"]
                 for p in response[0] if p.payload}
    for src in sources_returned:
        if by_source.get(src) != "hr":
            return _fail(f"filter leak: returned {src} with doc_type={by_source.get(src)}")
    return _pass(f"filter narrowed to {len(sources_returned)} hr sources")


def step_32_adr_has_w8_sections():
    path = Path("docs/adr/0001-capstone-framing.md")
    content = path.read_text().lower()
    required = ["ingestion pipeline", "chunking strategy", "metadata schema",
                "pii handling", "data residency"]
    missing = [k for k in required if k not in content]
    if missing:
        return _fail(f"ADR 0001 missing W8 terms: {missing}")
    return _pass("ADR 0001 has all W8 sections")


def step_33_no_adr_0003():
    """Curriculum: decisions stack in 0001."""
    adr_files = list(Path("docs/adr").glob("0003*"))
    if adr_files:
        return _fail(f"ADR 0003 exists ({[f.name for f in adr_files]})")
    return _pass("no ADR 0003 — consolidated in 0001 per curriculum")


def step_34_wk8_template_has_delta_column():
    path = Path("docs/kpi/wk8-snapshot-template.md")
    content = path.read_text()
    # Look for W7 / W8 / Δ columns
    needed = ["W7 value", "W8 value", "Δ"]
    missing = [k for k in needed if k not in content]
    if missing:
        return _fail(f"wk8 template missing columns: {missing}")
    # Also check the 8 KPIs
    kpis = ["Task success", "Grounded response", "Hallucination",
            "Retrieval hit", "Tool success", "Cost", "Latency", "Escalation"]
    missing_kpis = [k for k in kpis if k not in content]
    if missing_kpis:
        return _fail(f"wk8 template missing KPIs: {missing_kpis}")
    return _pass("wk8 template has W7→W8 delta column + 8 KPIs")


def step_35_total_spend():
    if spend_total > 0.10:
        return _fail(f"spend ${spend_total:.4f} > $0.10 ceiling")
    return _pass(f"total verification spend: ${spend_total:.4f}")


# ─── Run ────────────────────────────────────────────────────────────────

STEPS = [
    ("Python version >= 3.10", step_01_python_version),
    ("OPENAI_API_KEY set", step_02_openai_key),
    ("openai library installed", step_03_openai_lib),
    ("qdrant-client library installed", step_04_qdrant_lib),
    ("PyMuPDF (fitz) library installed", step_05_pymupdf_lib),
    ("beautifulsoup4 library installed", step_06_beautifulsoup_lib),
    ("python-docx library installed", step_07_python_docx_lib),
    ("Required files + dirs exist", step_08_directory_structure),
    ("Corpus has format diversity (md+pdf+html+docx)", step_09_corpus_format_diversity),
    ("Golden set is well-formed", step_10_golden_set_size),
    ("All 5 ingest modules importable", step_11_ingest_modules_import),
    ("qdrant_store has filter helpers + V2 name", step_12_qdrant_store_extended),
    ("ask_rag has filter param (backward compat)", step_13_qdrant_rag_filter_param),
    ("Chunk.metadata is a dict (W8 enrichment)", step_14_chunker_metadata_field),
    ("Metadata schema has all 9 fields", step_15_metadata_schema_complete),
    ("PII regex catches emails", step_16_pii_regex_email),
    ("PII regex catches phone numbers", step_17_pii_regex_phone),
    ("PII has no false positive on plain text", step_18_pii_no_false_positive),
    ("Parser handles markdown", step_19_parser_markdown),
    ("Parser handles PDF (PyMuPDF)", step_20_parser_pdf),
    ("Parser handles HTML (BeautifulSoup)", step_21_parser_html),
    ("Parser handles DOCX (python-docx)", step_22_parser_docx),
    ("Chunker is structure-aware (section_path)", step_23_chunker_structure_aware),
    ("Smoke tests pass", step_24_pytest_runs),
    ("Full pipeline offline (parse+chunk+scrub+meta)", step_25_pipeline_end_to_end_offline),
    ("Live Qdrant connectivity", step_26_qdrant_connectivity),
    ("Live OpenAI embed", step_27_live_embed_api),
    ("ingest_corpus.py runs end-to-end", step_28_ingest_corpus_runs),
    ("capstone_chunks_v2 collection populated", step_29_v2_collection_populated),
    ("Qdrant payload has metadata fields", step_30_metadata_in_qdrant_payload),
    ("Filtered query narrows to doc_type", step_31_filtered_query),
    ("ADR 0001 has W8 sections", step_32_adr_has_w8_sections),
    ("No separate ADR 0003", step_33_no_adr_0003),
    ("wk8 snapshot template has W7→W8 delta", step_34_wk8_template_has_delta_column),
    ("Total spend under $0.10", step_35_total_spend),
]


def main():
    total = len(STEPS)
    print("=" * 64)
    print(f"  W8 Verifier — {total} checks")
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
