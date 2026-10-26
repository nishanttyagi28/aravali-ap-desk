"""PDF loading via pdfplumber with optional OCR."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pdfplumber
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from docai.ingest.errors import IngestError
from docai.ingest.models import Document, PageInfo, Word, WordSource
from docai.ingest.ocr import OCR_DPI, ocr_page_image

_MIN_TEXT_CHARS_PER_PAGE = 12


def _plumber_word_to_word(w: dict, page: int, page_height: float) -> Word:
    return Word(
        text=w["text"],
        page=page,
        x0=float(w["x0"]),
        y0=page_height - float(w["bottom"]),
        x1=float(w["x1"]),
        y1=page_height - float(w["top"]),
        source=WordSource.TEXT_LAYER,
    )


def _render_page_for_ocr(pdf_path: Path, page_index: int) -> tuple[object, float, float]:
    import numpy as np
    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument(str(pdf_path))
    try:
        page = pdf[page_index]
        width_pt, height_pt = page.get_size()
        scale = OCR_DPI / 72.0
        bitmap = page.render(scale=scale)
        pil_image = bitmap.to_pil()
        image = np.array(pil_image.convert("RGB"))
        return image, float(width_pt), float(height_pt)
    finally:
        pdf.close()


def load_document(path: str | Path) -> Document:
    """Load a PDF into a :class:`Document` with words in PDF user-space bboxes."""
    pdf_path = Path(path)
    if not pdf_path.is_file():
        raise IngestError(f"File not found: {pdf_path}")

    raw = pdf_path.read_bytes()
    if not raw:
        raise IngestError("File is empty")

    sha256 = hashlib.sha256(raw).hexdigest()

    if not raw.lstrip().startswith(b"%PDF"):
        raise IngestError("Not a PDF file (missing %PDF header)")

    try:
        reader = PdfReader(str(pdf_path))
    except PdfReadError as exc:
        raise IngestError(f"Corrupted or unreadable PDF: {exc}") from exc

    if reader.is_encrypted:
        try:
            if reader.decrypt("") == 0:
                raise IngestError("PDF is password-protected")
        except Exception as exc:
            raise IngestError("PDF is password-protected") from exc

    page_count = len(reader.pages)
    if page_count < 1:
        raise IngestError("PDF has no pages")

    pages: list[PageInfo] = []
    words: list[Word] = []

    try:
        with pdfplumber.open(pdf_path) as pdf:
            if len(pdf.pages) != page_count:
                page_count = len(pdf.pages)

            for idx, page in enumerate(pdf.pages):
                page_num = idx + 1
                height = float(page.height)
                width = float(page.width)
                pages.append(PageInfo(width=width, height=height))

                page_words = page.extract_words(
                    keep_blank_chars=False,
                    use_text_flow=True,
                    extra_attrs=[],
                )
                converted = [_plumber_word_to_word(w, page_num, height) for w in page_words]
                text_len = sum(len(w.text) for w in converted)

                if text_len < _MIN_TEXT_CHARS_PER_PAGE:
                    image, w_pt, h_pt = _render_page_for_ocr(pdf_path, idx)
                    ocr_words = ocr_page_image(image, page_num, w_pt, h_pt)
                    words.extend(ocr_words)
                else:
                    words.extend(converted)
    except IngestError:
        raise
    except Exception as exc:
        raise IngestError(f"Failed to read PDF: {exc}") from exc

    if not pages:
        raise IngestError("PDF has no pages")

    return Document(
        sha256=sha256,
        page_count=len(pages),
        pages=pages,
        words=words,
        source_path=str(pdf_path.resolve()),
    )
