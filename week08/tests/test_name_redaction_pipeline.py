from pathlib import Path
from unittest.mock import patch

from src.ingest.pipeline import ingest_corpus


def test_name_redaction_before_embedding(tmp_path):
    document = tmp_path / "security_policy.md"
    document.write_text(
        "# Security Policy\n\n"
        "Contact Fatima Al-Rashid at +971 4 555 9876 "
        "for assistance.\n"
    )

    captured = {}

    def fake_embed(texts, model):
        captured["embedded_texts"] = texts
        return [[0.0] * 1536 for _ in texts]

    def fake_upsert(chunks, vectors, embedding_model, dim,
                    collection_name, reset):
        captured["stored_texts"] = [c.text for c in chunks]
        captured["metadata"] = [c.metadata for c in chunks]

    with patch("src.ingest.pipeline.embed", side_effect=fake_embed), \
         patch("src.ingest.pipeline._upsert_to_qdrant",
               side_effect=fake_upsert):
        result = ingest_corpus(
            corpus_dir=tmp_path,
            collection_name="test_redaction_only",
        )

    assert result.n_chunks >= 1

    for text in (
        captured["embedded_texts"]
        + captured["stored_texts"]
    ):
        assert "Fatima Al-Rashid" not in text
        assert "+971 4 555 9876" not in text
        assert "[PERSON]" in text
        assert "[PHONE]" in text

    assert any(
        "PERSON" in (metadata.get("pii_types") or [])
        for metadata in captured["metadata"]
    )
