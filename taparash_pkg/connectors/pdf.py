"""
PDF connector for Taparash.

Parses PDF files into DocumentChunks, preserving page numbers, headings
(detected by font size), and table presence.

Requires: pip install taparash[connectors]
Backend: pymupdf (fitz) — fast, handles both text-native and scanned PDFs.
"""

from pathlib import Path
from typing import List, Optional, Union

try:
    from taparash.config import DocumentChunk
except ImportError:
    from config import DocumentChunk  # type: ignore[no-redef]

try:
    import fitz  # type: ignore  # pymupdf

    _PYMUPDF = True
except ImportError:
    _PYMUPDF = False


def load_pdf(
    source: Union[str, Path],
    chunk_by: str = "page",
    min_chunk_chars: int = 40,
    heading_size_ratio: float = 1.2,
) -> List[DocumentChunk]:
    """
    Parse a PDF file into a list of DocumentChunks.

    Args:
        source:             Path to a PDF file.
        chunk_by:           Granularity: "page" (default) returns one chunk per page;
                            "block" returns one chunk per text block (finer grain).
        min_chunk_chars:    Discard chunks shorter than this (headers/footers/noise).
        heading_size_ratio: A text span is treated as a heading if its font size is
                            >= (median_body_font_size * heading_size_ratio).
                            Default 1.2 means 20% larger than body text.

    Returns:
        List[DocumentChunk] with metadata keys:
            source_file, format, page_num, heading, is_table, block_index

    Raises:
        ImportError: pymupdf is not installed.
        ValueError:  File does not exist or is not a PDF.
    """
    if not _PYMUPDF:
        raise ImportError(
            "PDF connector requires pymupdf.\n"
            "Install with: pip install taparash[connectors]"
        )

    path = Path(source)
    if not path.exists():
        raise ValueError(f"PDF file not found: {path}")
    if path.suffix.lower() != ".pdf":
        raise ValueError(f"Expected a .pdf file, got: {path.suffix}")

    doc = fitz.open(str(path))
    try:
        if chunk_by == "page":
            return _chunk_by_page(doc, path, min_chunk_chars, heading_size_ratio)
        return _chunk_by_block(doc, path, min_chunk_chars, heading_size_ratio)
    finally:
        doc.close()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _median_font_size(page: "fitz.Page") -> float:
    """Return the median font size of all text spans on the page."""
    sizes = []
    for block in page.get_text("dict")["blocks"]:
        if block["type"] != 0:  # 0 = text block
            continue
        for line in block["lines"]:
            for span in line["spans"]:
                sizes.append(span["size"])
    if not sizes:
        return 12.0
    sizes.sort()
    mid = len(sizes) // 2
    return sizes[mid]


def _extract_page_chunks(
    page: "fitz.Page",
    page_num: int,
    source_file: str,
    min_chunk_chars: int,
    heading_size_ratio: float,
    by_block: bool,
) -> List[DocumentChunk]:
    """Extract DocumentChunks from a single page."""
    median_size = _median_font_size(page)
    heading_threshold = median_size * heading_size_ratio

    # Check whether pymupdf detected any tables on this page
    tables = page.find_tables()
    table_bboxes = [t.bbox for t in tables] if tables else []

    current_heading: Optional[str] = None
    chunks: List[DocumentChunk] = []
    block_index = 0

    page_dict = page.get_text("dict")

    for block in page_dict["blocks"]:
        if block["type"] != 0:
            continue  # skip image blocks

        # Collect all spans in the block; detect headings
        block_texts = []
        block_is_heading = False
        for line in block["lines"]:
            for span in line["spans"]:
                span_text = span["text"].strip()
                if not span_text:
                    continue
                if span["size"] >= heading_threshold:
                    block_is_heading = True
                block_texts.append(span_text)

        full_text = " ".join(block_texts).strip()
        if not full_text:
            continue

        if block_is_heading and len(full_text) < 200:
            current_heading = full_text
            if not by_block:
                continue  # headings are metadata, not standalone chunks in page mode

        if len(full_text) < min_chunk_chars:
            continue

        # Determine if this block overlaps a detected table bbox
        block_rect = fitz.Rect(block["bbox"])
        is_table = any(block_rect.intersects(fitz.Rect(tb)) for tb in table_bboxes)

        meta = {
            "source_file": source_file,
            "format": "pdf",
            "page_num": page_num,
            "heading": current_heading,
            "is_table": is_table,
            "block_index": block_index,
        }
        chunks.append(DocumentChunk(text=full_text, metadata=meta))
        block_index += 1

    return chunks


def _chunk_by_page(
    doc: "fitz.Document",
    path: Path,
    min_chunk_chars: int,
    heading_size_ratio: float,
) -> List[DocumentChunk]:
    """One DocumentChunk per page (full page text concatenated)."""
    chunks: List[DocumentChunk] = []
    source_file = str(path)

    for page_num, page in enumerate(doc, start=1):
        # Collect per-block chunks to extract heading and table metadata,
        # then merge the text into a single page chunk.
        block_chunks = _extract_page_chunks(
            page, page_num, source_file, min_chunk_chars=1,
            heading_size_ratio=heading_size_ratio, by_block=True,
        )
        if not block_chunks:
            continue

        page_text = "\n\n".join(c.text for c in block_chunks)
        if len(page_text) < min_chunk_chars:
            continue

        # Use the first heading found on the page (if any)
        first_heading = next((c.metadata["heading"] for c in block_chunks if c.metadata["heading"]), None)
        has_table = any(c.metadata["is_table"] for c in block_chunks)

        meta = {
            "source_file": source_file,
            "format": "pdf",
            "page_num": page_num,
            "heading": first_heading,
            "is_table": has_table,
            "block_index": 0,
        }
        chunks.append(DocumentChunk(text=page_text, metadata=meta))

    return chunks


def _chunk_by_block(
    doc: "fitz.Document",
    path: Path,
    min_chunk_chars: int,
    heading_size_ratio: float,
) -> List[DocumentChunk]:
    """One DocumentChunk per text block (finer granularity)."""
    chunks: List[DocumentChunk] = []
    source_file = str(path)

    for page_num, page in enumerate(doc, start=1):
        chunks.extend(
            _extract_page_chunks(
                page, page_num, source_file, min_chunk_chars,
                heading_size_ratio, by_block=True,
            )
        )

    return chunks
