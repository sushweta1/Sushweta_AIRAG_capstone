"""Week 10 — Knowledge base version tests."""

import pytest

from src.rag.kb_version import (
    get_kb_version,
    next_kb_version,
    set_kb_version,
    validate_version,
)


def test_default_version(tmp_path):

    path = tmp_path / "version.json"

    assert get_kb_version(path) == "v2.w10"


def test_first_version_increment():

    assert next_kb_version("v2.w10") == "v2.w10.1"


def test_subsequent_version_increment():

    assert next_kb_version("v2.w10.9") == "v2.w10.10"


def test_version_persistence(tmp_path):

    path = tmp_path / "version.json"

    set_kb_version("v2.w10.1", path)

    assert get_kb_version(path) == "v2.w10.1"


def test_version_overwrite(tmp_path):

    path = tmp_path / "version.json"

    set_kb_version("v2.w10.1", path)
    set_kb_version("v2.w10.2", path)

    assert get_kb_version(path) == "v2.w10.2"


def test_invalid_version_rejected():

    with pytest.raises(ValueError):
        validate_version("invalid")


def test_invalid_write_preserves_version(tmp_path):

    path = tmp_path / "version.json"

    set_kb_version("v2.w10.1", path)

    with pytest.raises(ValueError):
        set_kb_version("v2.w10.0", path)

    assert get_kb_version(path) == "v2.w10.1"


def test_corrupt_version_file_rejected(tmp_path):

    path = tmp_path / "version.json"
    path.write_text("invalid json")

    with pytest.raises(ValueError):
        get_kb_version(path)
