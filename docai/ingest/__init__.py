"""PDF ingest (M2 — agent A)."""

from docai.ingest.errors import IngestError, OcrUnavailable
from docai.ingest.models import Document, PageInfo, Word, WordSource
from docai.ingest.pdf import load_document

__all__ = [
    "Document",
    "IngestError",
    "OcrUnavailable",
    "PageInfo",
    "Word",
    "WordSource",
    "load_document",
]
