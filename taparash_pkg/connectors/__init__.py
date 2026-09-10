"""
Taparash document connectors — parse structured formats into DocumentChunks.

Each connector returns List[DocumentChunk] ready for process_batch().
Install the required extras first:

    pip install taparash[connectors]        # pdf, html, pptx, docx
    pip install taparash[connectors-full]   # + unstructured (all formats)
"""

from .html import load_html
from .pdf import load_pdf

__all__ = ["load_html", "load_pdf"]
