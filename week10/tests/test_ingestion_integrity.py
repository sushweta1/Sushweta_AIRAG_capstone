"""Regression tests for source-text preservation during chunking."""

from src.ingest.parsers import ParsedDocument, ParsedSection
from src.ingest.chunkers import chunk_document


def make_document(text):
    return ParsedDocument(
        source="sample_policy.pdf",
        doc_title="Sample Policy",
        doc_type="pdf",
        sections=[
            ParsedSection(
                heading="Page 1",
                text=text,
                page=1,
                level=2,
            )
        ],
        raw_text=text,
    )


def test_short_policy_preserves_complete_text():
    text = (
        "Expense Policy\n"
        "US meal allowance is USD 80 per day.\n"
        "Claims must be submitted within 30 days."
    )

    chunks = chunk_document(make_document(text))

    assert len(chunks) >= 1
    combined = "\n".join(chunk.text for chunk in chunks)

    assert "USD 80" in combined
    assert "within 30 days" in combined
    assert "Claims must be submitted within 30 days." in combined


def test_long_policy_preserves_approval_threshold():
    text = (
        "Business travel requires manager approval.\n\n"
        + ("Travel receipts must be retained. " * 25)
        + "\n\n"
        + "Training expenses above GBP 1,000 require Director approval."
    )

    chunks = chunk_document(
        make_document(text),
        target_size=200,
        max_size=300,
        overlap=50,
    )

    combined = "\n".join(chunk.text for chunk in chunks)

    assert len(chunks) > 1
    assert "GBP 1,000" in combined
    assert "Director approval" in combined


def test_sliding_window_preserves_final_sentence():
    text = (
        "Policy requirements apply to all employees. " * 30
        + "Final approval must be recorded."
    )

    chunks = chunk_document(
        make_document(text),
        target_size=150,
        max_size=200,
        overlap=30,
    )

    combined = "\n".join(chunk.text for chunk in chunks)

    assert len(chunks) > 1
    assert "Final approval must be recorded." in combined


def test_multiple_pages_preserve_source_metadata():
    document = ParsedDocument(
        source="sample_policy.pdf",
        doc_title="Sample Policy",
        doc_type="pdf",
        sections=[
            ParsedSection(
                heading="Page 1",
                text="First page: GBP 40 meal allowance.",
                page=1,
                level=2,
            ),
            ParsedSection(
                heading="Page 2",
                text="Second page: receipts required.",
                page=2,
                level=2,
            ),
        ],
        raw_text="",
    )

    chunks = chunk_document(document)

    assert len(chunks) >= 2

    combined = "\n".join(chunk.text for chunk in chunks)

    assert "GBP 40" in combined
    assert "receipts required" in combined
    assert all(chunk.source == "sample_policy.pdf" for chunk in chunks)
