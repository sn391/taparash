"""
HTML connector for Taparash.

Parses HTML files or strings into DocumentChunks, extracting main content
and preserving structural metadata (title, headings, tables).

Requires: pip install taparash[connectors]
Primary backend: trafilatura  (lightweight, strips boilerplate automatically)
Fallback backend: beautifulsoup4 (used when trafilatura is not installed)
"""

from pathlib import Path
from typing import List, Optional, Union

try:
    from taparash.config import DocumentChunk
except ImportError:
    from config import DocumentChunk  # type: ignore[no-redef]

# ---------------------------------------------------------------------------
# Optional dependency checks
# ---------------------------------------------------------------------------
try:
    import trafilatura  # type: ignore

    _TRAFILATURA = True
except ImportError:
    _TRAFILATURA = False

try:
    from bs4 import BeautifulSoup  # type: ignore

    _BS4 = True
except ImportError:
    _BS4 = False


def load_html(
    source: Union[str, Path],
    source_url: Optional[str] = None,
    chunk_by: str = "paragraph",
    min_chunk_chars: int = 40,
) -> List[DocumentChunk]:
    """
    Parse an HTML file or raw HTML string into a list of DocumentChunks.

    Args:
        source:          Path to an HTML file, or a raw HTML string.
        source_url:      Optional URL to record in metadata (for web-fetched HTML).
        chunk_by:        Granularity of chunks: "paragraph" (default) or "page"
                         ("page" returns the full extracted text as one chunk).
        min_chunk_chars: Discard chunks shorter than this (noise/nav fragments).

    Returns:
        List[DocumentChunk] with metadata keys:
            source_file, format, heading, is_table, chunk_index

    Raises:
        ImportError:  Neither trafilatura nor beautifulsoup4 is installed.
        ValueError:   source is a Path that does not exist.
    """
    if not _TRAFILATURA and not _BS4:
        raise ImportError(
            "HTML connector requires trafilatura or beautifulsoup4.\n"
            "Install with: pip install taparash[connectors]"
        )

    # Resolve raw HTML string
    if isinstance(source, Path) or (isinstance(source, str) and not source.lstrip().startswith("<")):
        path = Path(source)
        if not path.exists():
            raise ValueError(f"HTML file not found: {path}")
        raw_html = path.read_text(encoding="utf-8", errors="replace")
        source_file = str(path)
    else:
        raw_html = source
        source_file = source_url or "<inline>"

    base_meta = {
        "source_file": source_file,
        "format": "html",
    }

    if _TRAFILATURA:
        return _parse_with_trafilatura(raw_html, base_meta, chunk_by, min_chunk_chars)
    return _parse_with_bs4(raw_html, base_meta, chunk_by, min_chunk_chars)


# ---------------------------------------------------------------------------
# trafilatura backend
# ---------------------------------------------------------------------------

def _parse_with_trafilatura(
    raw_html: str,
    base_meta: dict,
    chunk_by: str,
    min_chunk_chars: int,
) -> List[DocumentChunk]:
    import trafilatura  # type: ignore

    # Extract main content; include tables and comments
    extracted = trafilatura.extract(
        raw_html,
        include_tables=True,
        include_comments=False,
        output_format="txt",
    )
    if not extracted:
        return []

    # Best-effort title extraction
    meta_obj = trafilatura.extract_metadata(raw_html)
    title = meta_obj.title if meta_obj and meta_obj.title else None

    if chunk_by == "page":
        meta = {**base_meta, "heading": title, "is_table": False, "chunk_index": 0}
        return [DocumentChunk(text=extracted.strip(), metadata=meta)]

    # Split by double-newline (paragraph boundaries trafilatura uses)
    paragraphs = [p.strip() for p in extracted.split("\n\n") if p.strip()]
    chunks: List[DocumentChunk] = []
    current_heading = title

    for i, para in enumerate(paragraphs):
        if len(para) < min_chunk_chars:
            continue

        # Trafilatura marks tables with a leading pipe character in some configs;
        # detect them heuristically.
        is_table = para.startswith("|") or "\t" in para

        meta = {
            **base_meta,
            "heading": current_heading,
            "is_table": is_table,
            "chunk_index": i,
        }
        chunks.append(DocumentChunk(text=para, metadata=meta))

    return chunks


# ---------------------------------------------------------------------------
# beautifulsoup4 fallback backend
# ---------------------------------------------------------------------------

_HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
_BLOCK_TAGS = {"p", "li", "td", "th", "blockquote", "pre", "div"}


def _parse_with_bs4(
    raw_html: str,
    base_meta: dict,
    chunk_by: str,
    min_chunk_chars: int,
) -> List[DocumentChunk]:
    from bs4 import BeautifulSoup  # type: ignore

    soup = BeautifulSoup(raw_html, "html.parser")

    # Remove script/style noise
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else None

    if chunk_by == "page":
        text = soup.get_text(separator="\n", strip=True)
        meta = {**base_meta, "heading": title, "is_table": False, "chunk_index": 0}
        return [DocumentChunk(text=text, metadata=meta)] if len(text) >= min_chunk_chars else []

    chunks: List[DocumentChunk] = []
    current_heading = title
    chunk_index = 0

    for tag in soup.find_all(_HEADING_TAGS | _BLOCK_TAGS):
        text = tag.get_text(separator=" ", strip=True)
        if not text or len(text) < min_chunk_chars:
            continue

        if tag.name in _HEADING_TAGS:
            current_heading = text
            continue

        is_table = tag.name in {"td", "th"} or bool(tag.find_parent("table"))
        meta = {
            **base_meta,
            "heading": current_heading,
            "is_table": is_table,
            "chunk_index": chunk_index,
        }
        chunks.append(DocumentChunk(text=text, metadata=meta))
        chunk_index += 1

    return chunks
