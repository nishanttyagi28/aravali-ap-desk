from io import BytesIO
from pathlib import Path

import pytest
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from docai.extract import extract_file
from docai.ingest import load_document

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = ROOT / "datasets" / "sample"


def _image_only_pdf(src: Path, dest: Path) -> None:
    pytest.importorskip("rapidocr_onnxruntime")
    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument(str(src))
    page = pdf[0]
    scale = 200 / 72.0
    bitmap = page.render(scale=scale)
    pil = bitmap.to_pil().convert("RGB")
    pdf.close()

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4
    c.drawInlineImage(pil, 0, 0, width=width, height=height)
    c.showPage()
    c.save()
    dest.write_bytes(buf.getvalue())


@pytest.mark.parametrize("pdf_name", sorted(p.name for p in SAMPLE.glob("*.pdf"))[:2])
def test_scanned_path_ocr(tmp_path: Path, pdf_name: str) -> None:
    pytest.importorskip("rapidocr_onnxruntime")
    src = SAMPLE / pdf_name
    scanned = tmp_path / f"scan_{pdf_name}"
    _image_only_pdf(src, scanned)

    doc = load_document(scanned)
    assert any(w.source == "ocr" for w in doc.words)
    extracted = extract_file(scanned)
    assert extracted.invoice_number or extracted.vendor_gstin
