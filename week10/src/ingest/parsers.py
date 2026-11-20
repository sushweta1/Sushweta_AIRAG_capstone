"""Document parsers — format-specific extraction.

Public API: parse_document(path) → ParsedDocument

Dispatches by file extension:
  .pdf  → PyMuPDF (fast text + page numbers)
  .html → BeautifulSoup (structure-aware)
  .docx → python-docx (paragraphs + headings)
  .md   → plain Markdown (split by # headings)
  .txt  → plain text (no structure)

Each parser returns a ParsedDocument with:
  - source: filename
  - doc_title: extracted from first H1 / title / filename
  - doc_type: inferred from path or filename
  - sections: list of ParsedSection (heading + text + page)
  - raw_text: full text for fallback chunking

W8 doesn't do OCR. Scanned PDFs (no text layer) return empty
sections — the parser flags this so the pipeline can skip or warn.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class ParsedSection:
    """A chunk of text with a heading and optional page number.

    For PDFs: page is the source page number (1-indexed).
    For HTML/DOCX/MD: page is None; heading carries the section hierarchy.
    """
    heading: str
    text: str
    page: Optional[int] = None
    level: int = 1  # heading level (h1=1, h2=2, ...) for hierarchy


@dataclass
class ParsedDocument:
    """The full output of parse_document()."""
    source: str
    doc_title: str
    doc_type: str
    sections: list[ParsedSection] = field(default_factory=list)
    raw_text: str = ""

    @property
    def has_content(self) -> bool:
        """False if the parser got nothing (e.g. scanned PDF without OCR)."""
        return bool(self.raw_text.strip() or any(s.text.strip() for s in self.sections))


# ─── Per-format parsers ─────────────────────────────────────────────────

def _parse_pdf(path: Path) -> ParsedDocument:
    """Parse a PDF with PyMuPDF.

    Returns one ParsedSection per page (pages are the natural unit
    for PDFs — extracting hierarchical headings is unreliable across
    PDF dialects). Section heading is "Page N".
    """
    try:
        import fitz  # PyMuPDF
    except ImportError as e:
        raise ImportError(
            "PyMuPDF not installed. Run: pip install pymupdf"
        ) from e

    doc = fitz.open(str(path))
    sections: list[ParsedSection] = []
    raw_parts: list[str] = []

    for page_num, page in enumerate(doc, start=1):
        text = page.get_text("text")
        if text.strip():
            sections.append(ParsedSection(
                heading=f"Page {page_num}",
                text=text,
                page=page_num,
                level=2,
            ))
            raw_parts.append(text)

    doc.close()

    # Heuristic title: first non-trivial line of page 1, or filename
    doc_title = path.stem
    if sections:
        first_text = sections[0].text.strip().split("\n")[0]
        if 5 <= len(first_text) <= 120:
            doc_title = first_text

    return ParsedDocument(
        source=path.name,
        doc_title=doc_title,
        doc_type=_infer_doc_type(path),
        sections=sections,
        raw_text="\n\n".join(raw_parts),
    )


def _parse_html(path: Path) -> ParsedDocument:
    """Parse HTML with BeautifulSoup.

    Walks the DOM, treats h1/h2/h3 as section breaks, accumulates
    paragraph + list text under each heading.
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError as e:
        raise ImportError(
            "BeautifulSoup not installed. Run: pip install beautifulsoup4"
        ) from e

    html = path.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")

    # Title extraction
    doc_title = path.stem
    if soup.title and soup.title.string:
        doc_title = soup.title.string.strip()
    elif soup.h1:
        doc_title = soup.h1.get_text(strip=True)

    # Section extraction — walk h1/h2/h3 and group content under each
    sections: list[ParsedSection] = []
    current_heading = "Introduction"
    current_level = 1
    current_text_parts: list[str] = []

    body = soup.body or soup
    for element in body.descendants:
        if not hasattr(element, "name") or element.name is None:
            continue
        if element.name in ("h1", "h2", "h3", "h4"):
            # Flush the previous section
            if current_text_parts:
                sections.append(ParsedSection(
                    heading=current_heading,
                    text="\n".join(current_text_parts),
                    level=current_level,
                ))
            current_heading = element.get_text(strip=True)
            current_level = int(element.name[1])
            current_text_parts = []
        elif element.name in ("p", "li"):
            text = element.get_text(" ", strip=True)
            if text:
                current_text_parts.append(text)

    # Flush the final section
    if current_text_parts:
        sections.append(ParsedSection(
            heading=current_heading,
            text="\n".join(current_text_parts),
            level=current_level,
        ))

    raw_text = soup.get_text("\n", strip=True)

    return ParsedDocument(
        source=path.name,
        doc_title=doc_title,
        doc_type=_infer_doc_type(path),
        sections=sections,
        raw_text=raw_text,
    )


def _parse_docx(path: Path) -> ParsedDocument:
    """Parse a DOCX with python-docx.

    Uses paragraph styles to detect headings (Heading 1 / Heading 2 /
    Heading 3). Falls back to all-paragraphs-under-one-heading if no
    styles are detected.
    """
    try:
        from docx import Document  # python-docx
    except ImportError as e:
        raise ImportError(
            "python-docx not installed. Run: pip install python-docx"
        ) from e

    doc = Document(str(path))

    doc_title = path.stem
    # python-docx exposes core_properties.title but it's often empty
    if doc.core_properties.title:
        doc_title = doc.core_properties.title

    sections: list[ParsedSection] = []
    raw_parts: list[str] = []
    current_heading = "Body"
    current_level = 1
    current_text_parts: list[str] = []

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue
        style_name = (para.style.name if para.style else "") or ""
        if style_name.startswith("Heading"):
            # Flush prior section
            if current_text_parts:
                section_text = "\n".join(current_text_parts)
                sections.append(ParsedSection(
                    heading=current_heading,
                    text=section_text,
                    level=current_level,
                ))
                raw_parts.append(f"## {current_heading}\n{section_text}")
            current_heading = text
            try:
                current_level = int(style_name.replace("Heading", "").strip() or "1")
            except ValueError:
                current_level = 1
            current_text_parts = []
            # Use the first H1 as document title if not already set
            if doc_title == path.stem and current_level == 1:
                doc_title = text
        else:
            current_text_parts.append(text)

    if current_text_parts:
        section_text = "\n".join(current_text_parts)
        sections.append(ParsedSection(
            heading=current_heading,
            text=section_text,
            level=current_level,
        ))
        raw_parts.append(f"## {current_heading}\n{section_text}")

    return ParsedDocument(
        source=path.name,
        doc_title=doc_title,
        doc_type=_infer_doc_type(path),
        sections=sections,
        raw_text="\n\n".join(raw_parts),
    )


def _parse_markdown(path: Path) -> ParsedDocument:
    """Parse Markdown — split by # headings."""
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")

    doc_title = path.stem
    sections: list[ParsedSection] = []
    current_heading = "Introduction"
    current_level = 1
    current_text_parts: list[str] = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            # Flush prior section
            if current_text_parts:
                sections.append(ParsedSection(
                    heading=current_heading,
                    text="\n".join(current_text_parts).strip(),
                    level=current_level,
                ))
            # Count the leading #s
            level = 0
            for ch in stripped:
                if ch == "#":
                    level += 1
                else:
                    break
            heading_text = stripped.lstrip("#").strip()
            current_heading = heading_text
            current_level = max(level, 1)
            current_text_parts = []
            # First H1 becomes the doc title
            if doc_title == path.stem and current_level == 1:
                doc_title = heading_text
        else:
            current_text_parts.append(line)

    if current_text_parts:
        sections.append(ParsedSection(
            heading=current_heading,
            text="\n".join(current_text_parts).strip(),
            level=current_level,
        ))

    return ParsedDocument(
        source=path.name,
        doc_title=doc_title,
        doc_type=_infer_doc_type(path),
        sections=sections,
        raw_text=text,
    )


def _parse_text(path: Path) -> ParsedDocument:
    """Parse plain text — no structure detection."""
    text = path.read_text(encoding="utf-8")
    return ParsedDocument(
        source=path.name,
        doc_title=path.stem,
        doc_type=_infer_doc_type(path),
        sections=[ParsedSection(heading="Body", text=text, level=1)],
        raw_text=text,
    )


# ─── Helpers ────────────────────────────────────────────────────────────

def _infer_doc_type(path: Path) -> str:
    """Crude doc_type inference from filename + parent dir.

    Heuristic: HR-related keywords → 'hr', IT-related → 'it',
    else 'general'. Real systems would use a proper taxonomy.
    """
    name = (path.stem + " " + str(path.parent)).lower()
    hr_keywords = ("leave", "wfh", "expense", "parental", "sick",
                   "performance", "vacation", "hr", "compensation")
    it_keywords = ("vpn", "security", "incident", "password", "it",
                   "device", "laptop", "access")
    if any(k in name for k in hr_keywords):
        return "hr"
    if any(k in name for k in it_keywords):
        return "it"
    return "general"


# ─── Public dispatch ────────────────────────────────────────────────────

def parse_document(path: str | Path) -> ParsedDocument:
    """Parse a document. Dispatches by file extension.

    Raises:
        FileNotFoundError if path doesn't exist.
        ValueError if extension is not supported.
        ImportError if the format-specific library isn't installed.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Document not found: {path}")

    ext = p.suffix.lower()
    if ext == ".pdf":
        return _parse_pdf(p)
    elif ext in (".html", ".htm"):
        return _parse_html(p)
    elif ext == ".docx":
        return _parse_docx(p)
    elif ext == ".md":
        return _parse_markdown(p)
    elif ext == ".txt":
        return _parse_text(p)
    else:
        raise ValueError(
            f"Unsupported extension: {ext!r}. "
            f"Supported: .pdf .html .htm .docx .md .txt"
        )


def detect_format(path: str | Path) -> str:
    """Return the format name for a given path (for logging / metadata)."""
    p = Path(path)
    ext = p.suffix.lower()
    return {
        ".pdf": "pdf",
        ".html": "html",
        ".htm": "html",
        ".docx": "docx",
        ".md": "markdown",
        ".txt": "text",
    }.get(ext, "unknown")
