"""Ingest errors."""


class IngestError(Exception):
    """Failed to load or parse a document."""


class OcrUnavailable(Exception):
    """No OCR backend (RapidOCR or Tesseract) is available."""
