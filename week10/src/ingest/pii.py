"""PII detection and redaction.

Two-layer approach:
  1. Regex baseline — catches emails, phone numbers, simple IDs.
     Fast, deterministic, no external deps.
  2. Presidio upgrade — catches names, addresses, organizations,
     credit cards, etc. via NER. Slower, downloads a ~50MB model
     on first use, but catches what regex can't.

Use scrub_pii(text) for regex-only (the default — always works).
Use scrub_pii(text, use_presidio=True) to add Presidio.

The function returns a dataclass with:
  - redacted: the text with PII replaced by tokens like [EMAIL], [NAME]
  - findings: a list of what was found (for audit logging)

W8 pedagogical note: this module is the curriculum's prescribed
"see regex catch 2 of 3, then add Presidio to catch 3 of 3" demo.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class PIIFinding:
    """One PII item that was detected and redacted."""
    pii_type: str       # "EMAIL", "PHONE", "PERSON", etc.
    matched_text: str   # the original substring (for the audit log only)
    start: int          # character offset in the original text
    end: int
    source: str         # "regex" or "presidio"


@dataclass
class ScrubResult:
    """Output of scrub_pii()."""
    redacted: str
    findings: list[PIIFinding] = field(default_factory=list)
    has_pii: bool = False


# ─── Regex patterns (baseline) ──────────────────────────────────────────

# Email — RFC-ish, deliberately permissive
EMAIL_RE = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)

# Phone — international + UK + US formats
# Matches: +44 7700 900123, (555) 123-4567, 555-123-4567, +1-555-123-4567
PHONE_RE = re.compile(
    r"(?:\+?\d{1,3}[\s-]?)?(?:\(\d{2,4}\)|\d{2,4})[\s-]?\d{3,4}[\s-]?\d{3,4}\b"
)

# SSN — US Social Security Number (XXX-XX-XXXX)
SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")

# NI — UK National Insurance number (AA 12 34 56 A)
NI_RE = re.compile(
    r"\b[A-CEGHJ-PR-TW-Z]{2}\s?\d{2}\s?\d{2}\s?\d{2}\s?[A-D]\b"
)

# Credit card — Luhn-eligible 13-19 digit blocks (rough)
CC_RE = re.compile(r"\b(?:\d[ -]*?){13,19}\b")


REGEX_PATTERNS = [
    ("EMAIL", EMAIL_RE),
    ("PHONE", PHONE_RE),
    ("SSN", SSN_RE),
    ("NI_NUMBER", NI_RE),
    # Credit card LAST to avoid stealing matches from PHONE
    ("CREDIT_CARD", CC_RE),
]


# ─── Public scrubber ────────────────────────────────────────────────────

def scrub_pii(text: str, use_presidio: bool = False) -> ScrubResult:
    """Scrub PII from text. Returns the redacted text + findings.

    Args:
        text: the input string.
        use_presidio: if True, also run Presidio NER for names /
            addresses / orgs. Requires presidio-analyzer + spaCy model.

    Returns:
        ScrubResult.
    """
    if not text:
        return ScrubResult(redacted="", findings=[], has_pii=False)

    findings: list[PIIFinding] = []

    # Layer 1 — regex pass
    redacted, regex_findings = _apply_regex(text)
    findings.extend(regex_findings)

    # Layer 2 — Presidio pass (optional)
    if use_presidio:
        try:
            redacted, presidio_findings = _apply_presidio(redacted)
            findings.extend(presidio_findings)
        except ImportError:
            # Presidio not available — fail soft
            pass

    return ScrubResult(
        redacted=redacted,
        findings=findings,
        has_pii=bool(findings),
    )


# ─── Regex pass ─────────────────────────────────────────────────────────

def _apply_regex(text: str) -> tuple[str, list[PIIFinding]]:
    """Replace regex matches with [TYPE] tokens. Returns (new_text, findings)."""
    findings: list[PIIFinding] = []

    # Pass 1 — collect all matches with their positions
    matches: list[tuple[int, int, str, str]] = []  # (start, end, type, text)
    for pii_type, pattern in REGEX_PATTERNS:
        for m in pattern.finditer(text):
            # Skip very short matches that are likely false positives
            # (e.g. a 13-digit number that's not actually a credit card)
            if pii_type == "CREDIT_CARD":
                digits_only = re.sub(r"[^\d]", "", m.group())
                if not (13 <= len(digits_only) <= 19):
                    continue
            matches.append((m.start(), m.end(), pii_type, m.group()))

    # Sort by start, dedupe overlaps (PHONE often overlaps CC for long numbers —
    # we keep the FIRST match by sort order, which is the one with the lower
    # start position; ties broken by longer span)
    matches.sort(key=lambda x: (x[0], -(x[1] - x[0])))
    dedup: list[tuple[int, int, str, str]] = []
    last_end = -1
    for start, end, pii_type, matched in matches:
        if start < last_end:
            continue  # overlapping match — skip
        dedup.append((start, end, pii_type, matched))
        last_end = end

    # Build the redacted string by walking through the dedupe matches
    if not dedup:
        return text, []
    parts: list[str] = []
    cursor = 0
    for start, end, pii_type, matched in dedup:
        parts.append(text[cursor:start])
        parts.append(f"[{pii_type}]")
        findings.append(PIIFinding(
            pii_type=pii_type,
            matched_text=matched,
            start=start,
            end=end,
            source="regex",
        ))
        cursor = end
    parts.append(text[cursor:])
    return "".join(parts), findings


# ─── Presidio pass (lazy import) ────────────────────────────────────────

_analyzer = None
_anonymizer = None


def _get_presidio():
    """Lazy-load Presidio. Raises ImportError if not installed."""
    global _analyzer, _anonymizer
    if _analyzer is None:
        from presidio_analyzer import AnalyzerEngine
        from presidio_anonymizer import AnonymizerEngine
        _analyzer = AnalyzerEngine()
        _anonymizer = AnonymizerEngine()
    return _analyzer, _anonymizer


# Presidio entities we care about. We deliberately limit to high-value
# entities to keep false positives down.
PRESIDIO_ENTITIES = [
    "PERSON",
    "LOCATION",
    "ORGANIZATION",
    "DATE_TIME",  # often noisy; included with conf threshold
    "IBAN_CODE",
    "US_PASSPORT",
    "US_DRIVER_LICENSE",
]


def _apply_presidio(text: str) -> tuple[str, list[PIIFinding]]:
    """Run Presidio's NER + anonymizer on text. Returns (new_text, findings).

    Findings here are tagged source='presidio' to distinguish in audits.
    """
    try:
        analyzer, anonymizer = _get_presidio()
    except ImportError:
        return text, []

    # Skip DATE_TIME if it's the only entity (too noisy on policy docs)
    entities = [e for e in PRESIDIO_ENTITIES if e != "DATE_TIME"]
    results = analyzer.analyze(text=text, entities=entities, language="en")
    # Filter by confidence — Presidio's default is 0.5; raise to 0.7 to
    # reduce false positives on policy text
    results = [r for r in results if r.score >= 0.7]

    if not results:
        return text, []

    findings = [
        PIIFinding(
            pii_type=r.entity_type,
            matched_text=text[r.start:r.end],
            start=r.start,
            end=r.end,
            source="presidio",
        )
        for r in results
    ]
    anonymized = anonymizer.anonymize(text=text, analyzer_results=results)
    return anonymized.text, findings


# ─── Convenience: bulk scrub for a list of chunks ────────────────────────

def scrub_chunks(chunks: list, use_presidio: bool = False) -> list:
    """Scrub PII from each chunk's text in-place, setting metadata.has_pii.

    Args:
        chunks: list of Chunk objects (from src.ingest.chunkers).
        use_presidio: passed through to scrub_pii.

    Returns:
        The same list, with each chunk's `text` redacted and
        `metadata["has_pii"]` set to True/False.
    """
    for chunk in chunks:
        result = scrub_pii(chunk.text, use_presidio=use_presidio)
        chunk.text = result.redacted
        if not isinstance(chunk.metadata, dict):
            chunk.metadata = {}
        chunk.metadata["has_pii"] = result.has_pii
        chunk.metadata["pii_types"] = sorted({f.pii_type for f in result.findings})
    return chunks
