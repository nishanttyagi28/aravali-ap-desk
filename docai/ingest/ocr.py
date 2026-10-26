"""OCR backends for scanned pages."""

from __future__ import annotations

from typing import TYPE_CHECKING

from docai.ingest.errors import OcrUnavailable
from docai.ingest.models import Word, WordSource

if TYPE_CHECKING:
    import numpy as np

OCR_DPI = 200


def _ocr_rapidocr(
    image: np.ndarray, page: int, page_width_pt: float, page_height_pt: float
) -> list[Word]:
    from rapidocr_onnxruntime import RapidOCR

    engine = RapidOCR()
    result, _ = engine(image)
    if not result:
        return []
    scale = 72.0 / OCR_DPI
    words: list[Word] = []
    for item in result:
        box, text, _score = item[0], str(item[1]).strip(), float(item[2])
        if not text:
            continue
        xs = [p[0] for p in box]
        ys = [p[1] for p in box]
        x0_px, x1_px = min(xs), max(xs)
        top_px, bottom_px = min(ys), max(ys)
        x0 = x0_px * scale
        x1 = x1_px * scale
        y0 = page_height_pt - bottom_px * scale
        y1 = page_height_pt - top_px * scale
        words.append(
            Word(
                text=text,
                page=page,
                x0=x0,
                y0=y0,
                x1=x1,
                y1=y1,
                source=WordSource.OCR,
            )
        )
    return words


def _ocr_tesseract(
    image: np.ndarray, page: int, page_width_pt: float, page_height_pt: float
) -> list[Word]:
    import pytesseract
    from pytesseract import Output

    data = pytesseract.image_to_data(image, output_type=Output.DICT)
    scale = 72.0 / OCR_DPI
    words: list[Word] = []
    n = len(data["text"])
    for i in range(n):
        text = (data["text"][i] or "").strip()
        if not text or int(data["conf"][i]) < 0:
            continue
        x_px = float(data["left"][i])
        w_px = float(data["width"][i])
        y_px = float(data["top"][i])
        h_px = float(data["height"][i])
        x0 = x_px * scale
        x1 = (x_px + w_px) * scale
        y0 = page_height_pt - (y_px + h_px) * scale
        y1 = page_height_pt - y_px * scale
        words.append(
            Word(
                text=text,
                page=page,
                x0=x0,
                y0=y0,
                x1=x1,
                y1=y1,
                source=WordSource.OCR,
            )
        )
    return words


def ocr_page_image(
    image: np.ndarray, page: int, page_width_pt: float, page_height_pt: float
) -> list[Word]:
    """Run OCR on a rendered page image; pixel boxes converted to PDF points."""
    try:
        import rapidocr_onnxruntime  # noqa: F401

        return _ocr_rapidocr(image, page, page_width_pt, page_height_pt)
    except ImportError:
        pass

    try:
        import shutil

        import pytesseract

        if shutil.which(pytesseract.pytesseract.tesseract_cmd or "tesseract"):
            return _ocr_tesseract(image, page, page_width_pt, page_height_pt)
    except ImportError:
        pass

    raise OcrUnavailable(
        "OCR is required for this document but neither rapidocr-onnxruntime nor "
        "pytesseract with a Tesseract binary is available. Install the 'ocr' extra "
        "or Tesseract, or use a PDF with a text layer."
    )
