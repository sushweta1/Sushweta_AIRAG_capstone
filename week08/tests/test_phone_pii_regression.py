import pytest
from src.ingest.pii import scrub_pii


@pytest.mark.parametrize("phone", [
    "+971 4 555 9876",
    "+44 7700 900123",
    "+1-555-123-4567",
    "(555) 123-4567",
])
def test_phone_numbers_are_fully_redacted(phone):
    result = scrub_pii(phone)
    assert result.redacted == "[PHONE]"


@pytest.mark.parametrize("text", [
    "20 days of annual leave",
    "2026-10-31",
])
def test_non_phone_text_is_unchanged(text):
    result = scrub_pii(text)
    assert result.redacted == text
