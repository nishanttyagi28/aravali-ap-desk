from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import api.deps as deps
import api.main as main_mod
from api.deps import build_state
from api.main import create_app
from docai.contracts.truth import TruthRecord

ROOT = Path(__file__).resolve().parents[2]
SAMPLE_DIR = ROOT / "datasets" / "sample"
SAMPLE_ID = "ad689cf8-8759-f153-b778-5728f2655b19"


def test_upload_sample_pdf_uses_real_extractor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    monkeypatch.setattr(deps, "UPLOAD_DIR", upload_dir)
    monkeypatch.setattr(main_mod, "UPLOAD_DIR", upload_dir)

    truth = TruthRecord.model_validate_json(
        (SAMPLE_DIR / f"{SAMPLE_ID}.truth.json").read_text(encoding="utf-8")
    )
    pdf_bytes = (SAMPLE_DIR / f"{SAMPLE_ID}.pdf").read_bytes()

    state = build_state(
        database_url=f"sqlite:///{tmp_path / 'api.db'}",
        extract_fn=None,
        vendor_master_path=SAMPLE_DIR / "vendor_master.json",
    )
    client = TestClient(create_app(state))
    resp = client.post(
        "/invoices",
        files={"file": (f"{SAMPLE_ID}.pdf", pdf_bytes, "application/pdf")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["invoice"]["invoice_number"] == truth.invoice.invoice_number
    assert body["decision"]["outcome"] == truth.expected_decision.value
