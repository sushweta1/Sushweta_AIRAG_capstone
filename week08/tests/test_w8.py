"""Smoke tests for W8 — no API calls.

Tests the new ingest/* modules + the qdrant_store extensions.

Run with: python -m pytest tests/ -v
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import _bootstrap  # noqa: F401

import pytest

from src.ingest.parsers import (
    detect_format, parse_document, ParsedDocument, ParsedSection,
)
from src.ingest.chunkers import Chunk, chunk_document
from src.ingest.pii import scrub_pii, scrub_chunks, ScrubResult, PIIFinding
from src.ingest.metadata import (
    METADATA_FIELDS, finalize_metadata, validate_metadata, summarize_metadata,
)


# ─── Format detection ───────────────────────────────────────────────────

def test_detect_format_pdf():
    assert detect_format("foo.pdf") == "pdf"
    assert detect_format("foo.PDF") == "pdf"


def test_detect_format_all():
    cases = {
        "x.pdf": "pdf",
        "x.html": "html",
        "x.htm": "html",
        "x.docx": "docx",
        "x.md": "markdown",
        "x.txt": "text",
        "x.unknown": "unknown",
    }
    for path, expected in cases.items():
        assert detect_format(path) == expected, f"{path} should detect as {expected}"


# ─── Markdown parser (no external deps) ─────────────────────────────────

def test_parse_markdown_basic(tmp_path):
    md = tmp_path / "test.md"
    md.write_text(
        "# Main Title\n\n"
        "Intro text.\n\n"
        "## Section A\n\n"
        "Section A content goes here.\n\n"
        "## Section B\n\n"
        "Section B content."
    )
    parsed = parse_document(md)
    assert isinstance(parsed, ParsedDocument)
    assert parsed.doc_title == "Main Title"
    assert parsed.source == "test.md"
    assert len(parsed.sections) >= 3
    # First section should be the Intro under Main Title
    titles = [s.heading for s in parsed.sections]
    assert "Main Title" in titles
    assert "Section A" in titles
    assert "Section B" in titles


def test_parse_markdown_doc_type_inference(tmp_path):
    md = tmp_path / "leave_policy.md"
    md.write_text("# Leave Policy\n\nContent.")
    parsed = parse_document(md)
    assert parsed.doc_type == "hr"

    md2 = tmp_path / "vpn_setup.md"
    md2.write_text("# VPN Setup\n\nContent.")
    parsed2 = parse_document(md2)
    assert parsed2.doc_type == "it"


def test_parse_text_file(tmp_path):
    txt = tmp_path / "test.txt"
    txt.write_text("Just some plain text.")
    parsed = parse_document(txt)
    assert parsed.raw_text == "Just some plain text."
    assert len(parsed.sections) == 1


def test_parse_nonexistent_raises():
    with pytest.raises(FileNotFoundError):
        parse_document("/tmp/does-not-exist.md")


def test_parse_unsupported_extension(tmp_path):
    weird = tmp_path / "foo.xyz"
    weird.write_text("?")
    with pytest.raises(ValueError):
        parse_document(weird)


# ─── Structure-aware chunker ────────────────────────────────────────────

def test_chunk_document_small_section_one_chunk():
    parsed = ParsedDocument(
        source="t.md", doc_title="T", doc_type="general",
        sections=[ParsedSection(heading="Sec", text="Short text.", level=1)],
        raw_text="Short text.",
    )
    chunks = chunk_document(parsed, target_size=500, max_size=800)
    assert len(chunks) == 1
    assert "Short text." in chunks[0].text
    assert chunks[0].metadata["heading"] == "Sec"
    assert chunks[0].metadata["doc_title"] == "T"


def test_chunk_document_preserves_section_path():
    """A nested heading hierarchy should produce section_path = 'A > B'."""
    parsed = ParsedDocument(
        source="t.md", doc_title="T", doc_type="general",
        sections=[
            ParsedSection(heading="A", text="A body", level=1),
            ParsedSection(heading="B", text="B body", level=2),
        ],
        raw_text="A body\n\nB body",
    )
    chunks = chunk_document(parsed)
    assert len(chunks) == 2
    # First chunk's section_path is just A
    assert chunks[0].metadata["section_path"] == "A"
    # Second chunk's section_path is A > B
    assert chunks[1].metadata["section_path"] == "A > B"


def test_chunk_document_large_section_splits():
    """A section bigger than max_size should split into multiple chunks."""
    big_text = "Paragraph one is here.\n\n" + ("Paragraph two is longer. " * 50)
    parsed = ParsedDocument(
        source="t.md", doc_title="T", doc_type="general",
        sections=[ParsedSection(heading="Big", text=big_text, level=1)],
        raw_text=big_text,
    )
    chunks = chunk_document(parsed, target_size=300, max_size=500)
    assert len(chunks) >= 2  # had to split
    # All chunks carry the parent heading
    for chunk in chunks:
        assert chunk.metadata["heading"] == "Big"


def test_chunk_document_empty_sections():
    parsed = ParsedDocument(
        source="t.md", doc_title="T", doc_type="general",
        sections=[], raw_text="",
    )
    chunks = chunk_document(parsed)
    assert chunks == []


# ─── PII scrubbing ──────────────────────────────────────────────────────

def test_scrub_pii_email():
    text = "Contact me at alice@example.com please."
    result = scrub_pii(text)
    assert "[EMAIL]" in result.redacted
    assert "alice@example.com" not in result.redacted
    assert result.has_pii
    assert any(f.pii_type == "EMAIL" for f in result.findings)


def test_scrub_pii_phone_uk():
    text = "Call +44 20 7946 0123 for support."
    result = scrub_pii(text)
    assert "[PHONE]" in result.redacted
    assert result.has_pii


def test_scrub_pii_phone_us():
    text = "Call (415) 555-0188 anytime."
    result = scrub_pii(text)
    assert "[PHONE]" in result.redacted


def test_scrub_pii_multiple_findings():
    text = "Email alice@example.com or call +44 20 7946 0123."
    result = scrub_pii(text)
    assert result.redacted.count("[EMAIL]") == 1
    assert result.redacted.count("[PHONE]") == 1
    assert len(result.findings) == 2


def test_scrub_pii_no_findings():
    text = "This is just plain text with no PII."
    result = scrub_pii(text)
    assert result.redacted == text
    assert not result.has_pii
    assert result.findings == []


def test_scrub_pii_ssn():
    text = "SSN: 123-45-6789 (do not share)."
    result = scrub_pii(text)
    assert "[SSN]" in result.redacted


def test_scrub_pii_empty_string():
    result = scrub_pii("")
    assert result.redacted == ""
    assert not result.has_pii


def test_scrub_chunks_sets_metadata():
    """scrub_chunks should set has_pii + pii_types on each chunk's metadata."""
    chunks = [
        Chunk(text="Contact alice@example.com.", source="t.md", metadata={}),
        Chunk(text="No PII here.", source="t.md", metadata={}),
    ]
    scrub_chunks(chunks)
    assert chunks[0].metadata["has_pii"] is True
    assert "EMAIL" in chunks[0].metadata["pii_types"]
    assert chunks[1].metadata["has_pii"] is False
    assert chunks[1].metadata["pii_types"] == []


# ─── Metadata ───────────────────────────────────────────────────────────

def test_metadata_fields_canonical():
    """The canonical list should include the 9 fields we promised."""
    expected = {"source", "doc_title", "doc_type", "section_path", "page",
                "ingested_at", "has_pii", "pii_types", "char_length"}
    assert expected.issubset(set(METADATA_FIELDS))


def test_finalize_metadata_fills_missing_fields():
    chunks = [Chunk(text="hi", source="t.md", metadata={"doc_title": "T"})]
    finalize_metadata(chunks)
    for field in METADATA_FIELDS:
        assert field in chunks[0].metadata


def test_validate_metadata_catches_missing_required():
    chunk = Chunk(text="hi", source="t.md", metadata={})
    errors = validate_metadata(chunk)
    assert errors  # should fail validation for missing required fields


def test_summarize_metadata_correct_counts():
    chunks = [
        Chunk(text="a", source="hr.md",
              metadata={"doc_type": "hr", "has_pii": True, "source": "hr.md"}),
        Chunk(text="b", source="hr.md",
              metadata={"doc_type": "hr", "has_pii": False, "source": "hr.md"}),
        Chunk(text="c", source="it.md",
              metadata={"doc_type": "it", "has_pii": False, "source": "it.md"}),
    ]
    summary = summarize_metadata(chunks)
    assert summary["n_chunks"] == 3
    assert summary["chunks_with_pii"] == 1
    assert summary["doc_types"]["hr"] == 2
    assert summary["doc_types"]["it"] == 1


# ─── Qdrant store imports (no live connection) ──────────────────────────

def test_qdrant_store_imports():
    from src.rag.qdrant_store import (
        QdrantStore, build_store, load_store, retrieve,
        collection_count, eq, combine_and, combine_or,
        COLLECTION_NAME, COLLECTION_NAME_V2,
    )
    assert COLLECTION_NAME == "capstone_chunks"
    assert COLLECTION_NAME_V2 == "capstone_chunks_v2"


def test_qdrant_filter_eq_builds():
    """eq() should produce a Qdrant Filter object."""
    from src.rag.qdrant_store import eq
    f = eq("doc_type", "hr")
    assert f is not None
    assert hasattr(f, "must")


def test_qdrant_filter_combine_and():
    from src.rag.qdrant_store import eq, combine_and
    f1 = eq("doc_type", "hr")
    f2 = eq("has_pii", False)
    combined = combine_and(f1, f2)
    # Combined filter should have 2 conditions
    assert combined is not None
    assert len(combined.must) == 2


def test_qdrant_inmemory_with_filter():
    """End-to-end: in-memory Qdrant with a metadata filter."""
    try:
        from qdrant_client import QdrantClient
        from qdrant_client.http import models as qmodels
    except ImportError:
        pytest.skip("qdrant-client not installed")

    client = QdrantClient(":memory:")
    client.create_collection(
        collection_name="t",
        vectors_config=qmodels.VectorParams(size=2, distance=qmodels.Distance.COSINE),
    )
    client.upsert(
        collection_name="t",
        points=[
            qmodels.PointStruct(id=1, vector=[1.0, 0.0],
                                  payload={"text": "hr-thing", "doc_type": "hr"}),
            qmodels.PointStruct(id=2, vector=[0.9, 0.1],
                                  payload={"text": "it-thing", "doc_type": "it"}),
        ],
    )

    # Filter by doc_type=hr — should only return point 1
    from src.rag.qdrant_store import eq
    response = client.query_points(
        collection_name="t",
        query=[1.0, 0.0],
        limit=5,
        query_filter=eq("doc_type", "hr"),
    )
    assert len(response.points) == 1
    assert response.points[0].payload["doc_type"] == "hr"


# ─── Integration: parse + chunk + scrub on a small sample ───────────────

def test_full_pipeline_on_markdown(tmp_path):
    """End-to-end pipeline test with no network calls."""
    md = tmp_path / "test_policy.md"
    md.write_text(
        "# Test Policy\n\n"
        "Contact john.doe@example.com or +1 (555) 123-4567 for help.\n\n"
        "## Procedure\n\n"
        "Submit forms via the portal."
    )

    parsed = parse_document(md)
    chunks = chunk_document(parsed)
    scrub_chunks(chunks)
    finalize_metadata(chunks)

    # At least one chunk has PII
    pii_chunks = [c for c in chunks if c.metadata["has_pii"]]
    assert pii_chunks

    # PII is actually redacted in the chunk text
    for c in pii_chunks:
        assert "john.doe@example.com" not in c.text
        assert "555" not in c.text or "[PHONE]" in c.text

    # All chunks have the full metadata schema
    for c in chunks:
        for field in METADATA_FIELDS:
            assert field in c.metadata
