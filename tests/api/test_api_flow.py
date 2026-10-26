import json
from pathlib import Path
from uuid import UUID

from fastapi.testclient import TestClient

from api.deps import build_state
from api.main import create_app
from datasets.synth.generator import generate_dataset
from docai.contracts.decision import DecisionOutcome
from docai.contracts.extracted import ExtractedInvoice
from docai.contracts.truth import TruthRecord


def _client_for_dataset(
    tmp_path: Path, cases: list[str]
) -> tuple[TestClient, dict[UUID, TruthRecord]]:
    generate_dataset(len(cases), 21, tmp_path, cases_override=cases)
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    master_path = tmp_path / "vendor_master.json"
    truths = {
        UUID(e["id"]): TruthRecord.model_validate_json(
            (tmp_path / f"{e['id']}.truth.json").read_text()
        )
        for e in manifest["invoices"]
    }

    def fake_extract(path: Path) -> ExtractedInvoice:
        digest = __import__("hashlib").sha256(path.read_bytes()).hexdigest()
        for truth in truths.values():
            if truth.invoice.sha256 == digest:
                return truth.invoice
        raise RuntimeError("unknown pdf")

    state = build_state(
        database_url=f"sqlite:///{tmp_path / 'api.db'}",
        extract_fn=fake_extract,
        vendor_master_path=master_path,
    )
    return TestClient(create_app(state)), truths


def test_review_correct_post_and_repost(tmp_path: Path) -> None:
    client, truths = _client_for_dataset(tmp_path, ["missing_invoice_date", "clean_intrastate"])
    review_id = next(iid for iid, t in truths.items() if t.invoice.invoice_date is None)

    for iid in truths:
        pdf = tmp_path / f"{iid}.pdf"
        resp = client.post(
            "/invoices", files={"file": (pdf.name, pdf.read_bytes(), "application/pdf")}
        )
        assert resp.status_code == 200
        if iid == review_id:
            assert resp.json()["decision"]["outcome"] == DecisionOutcome.REVIEW.value

    corr = client.post(
        f"/invoices/{review_id}/review",
        json={
            "action": "correct",
            "reviewer": "alice",
            "corrections": {"invoice_date": "2025-04-15"},
        },
    )
    assert corr.status_code == 200
    assert corr.json()["decision"]["outcome"] == DecisionOutcome.ALLOW.value

    post = client.post(f"/invoices/{review_id}/post")
    assert post.status_code == 200
    again = client.post(f"/invoices/{review_id}/post")
    assert again.status_code == 409
    assert again.json()["code"] == "already_posted"


def test_block_cannot_approve(tmp_path: Path) -> None:
    client, truths = _client_for_dataset(tmp_path, ["bad_gstin_checksum"])
    inv_id = next(iter(truths))
    pdf = tmp_path / f"{inv_id}.pdf"
    client.post("/invoices", files={"file": (pdf.name, pdf.read_bytes(), "application/pdf")})
    resp = client.post(
        f"/invoices/{inv_id}/review",
        json={"action": "approve", "reviewer": "bob"},
    )
    assert resp.status_code == 409
    post = client.post(f"/invoices/{inv_id}/post")
    assert post.status_code == 409
