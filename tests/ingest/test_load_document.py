from pathlib import Path

import pytest

from docai.ingest import IngestError, load_document

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = ROOT / "datasets" / "sample"


def test_load_sample_pdf_has_words() -> None:
    pdf = next(SAMPLE.glob("*.pdf"))
    doc = load_document(pdf)
    assert doc.page_count >= 1
    assert doc.sha256
    assert len(doc.words) > 20
    assert all(w.y0 <= w.y1 for w in doc.words)


def test_ingest_empty_file(tmp_path: Path) -> None:
    p = tmp_path / "empty.pdf"
    p.write_bytes(b"")
    with pytest.raises(IngestError, match="empty"):
        load_document(p)


def test_ingest_not_pdf(tmp_path: Path) -> None:
    p = tmp_path / "notes.txt"
    p.write_text("hello", encoding="utf-8")
    with pytest.raises(IngestError, match="Not a PDF"):
        load_document(p)


def test_ingest_missing_file() -> None:
    with pytest.raises(IngestError, match="not found"):
        load_document(SAMPLE / "missing.pdf")
