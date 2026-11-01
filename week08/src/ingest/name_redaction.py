"""Targeted name redaction for the Week 8 lab corpus.

This is a corpus-specific safeguard, not general-purpose
named-entity recognition.
"""

import re

KNOWN_NAMES = (
    "Fatima Al-Rashid",
    "Marcus Johnson",
    "Priya Sharma",
    "Rajesh Patel",
    "Yuki Tanaka",
    "Aisha Mohammed",
    "Carlos Rodriguez",
    "Mei Chen",
    "David Okafor",
    "Fatima",
)

NAME_PATTERN = re.compile(
    r"(?<!\w)(?:"
    + "|".join(re.escape(name) for name in KNOWN_NAMES)
    + r")(?!\w)",
    re.IGNORECASE,
)


def redact_known_names(text: str) -> str:
    """Replace known personal names with [PERSON]."""
    return NAME_PATTERN.sub("[PERSON]", text)
