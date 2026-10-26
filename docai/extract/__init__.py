"""Invoice extraction (M2 — agent A)."""

from __future__ import annotations

from pathlib import Path

from docai.contracts.extracted import ExtractedInvoice, ExtractionMode
from docai.extract.llm import LLMFallback
from docai.extract.offline import extract_offline
from docai.ingest import load_document
from docai.ingest.models import Document

_LOW_CONF_THRESHOLD = 0.5


def extract(
    document: Document, *, mode: str = "offline", llm: LLMFallback | None = None
) -> ExtractedInvoice:
    """Extract structured invoice fields from an ingested document."""
    extraction_mode = ExtractionMode(mode)
    source_file = document.source_path or "unknown.pdf"
    name = Path(source_file).name

    invoice = extract_offline(document, name)

    if extraction_mode == ExtractionMode.LLM and llm is not None:
        missing = [
            k
            for k, f in invoice.fields.items()
            if f.confidence < _LOW_CONF_THRESHOLD or f.value is None
        ]
        if missing:
            suggestions = llm.suggest_fields(document, missing, invoice.fields)
            for key, field in suggestions.items():
                invoice.fields[key] = field
                if hasattr(invoice, key):
                    setattr(invoice, key, field.value)

    return invoice


def extract_file(
    path: Path, *, mode: str = "offline", llm: LLMFallback | None = None
) -> ExtractedInvoice:
    """Load a PDF from disk and extract an invoice."""
    document = load_document(path)
    return extract(document, mode=mode, llm=llm)


__all__ = ["LLMFallback", "extract", "extract_file"]
