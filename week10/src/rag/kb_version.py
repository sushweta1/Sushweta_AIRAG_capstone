"""Week 10 — Persistent knowledge base version management."""

import json
import os
import re
import tempfile
from pathlib import Path
from datetime import datetime, timezone


BASE_VERSION = "v2.w10"
DEFAULT_VERSION_PATH = "data/kb_version.json"

_VERSION_RE = re.compile(r"v2\.w10(?:\.[1-9]\d*)?")


def validate_version(version: str) -> str:
    """Validate a Week 10 knowledge base version."""

    if not isinstance(version, str):
        raise ValueError("KB version must be a string.")

    if not _VERSION_RE.fullmatch(version):
        raise ValueError(f"Invalid KB version: {version}")

    return version


def get_kb_version(
    path=DEFAULT_VERSION_PATH,
) -> str:
    """Read the current persisted KB version."""

    version_path = Path(path)

    if not version_path.exists():
        return BASE_VERSION

    data = json.loads(
        version_path.read_text(encoding="utf-8")
    )

    return validate_version(data["kb_version"])


def next_kb_version(current: str) -> str:
    """Calculate the next version without writing state."""

    validate_version(current)

    if current == BASE_VERSION:
        return f"{BASE_VERSION}.1"

    revision = int(current.rsplit(".", 1)[1])

    return f"{BASE_VERSION}.{revision + 1}"


def set_kb_version(
    version: str,
    path=DEFAULT_VERSION_PATH,
) -> str:
    """Persist a version using atomic file replacement."""

    validate_version(version)

    version_path = Path(path)
    version_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    data = {
        "kb_version": version,
        "updated_at": datetime.now(
            timezone.utc
        ).isoformat(),
    }

    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=version_path.parent,
            delete=False,
        ) as temp:

            temp_path = Path(temp.name)

            json.dump(data, temp, indent=2)

            temp.flush()
            os.fsync(temp.fileno())

        os.replace(temp_path, version_path)

    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink()

    return version
