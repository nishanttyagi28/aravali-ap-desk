"""End-to-end API flow with real offline extraction."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

import api.deps as deps
import api.main as main_mod
from api.deps import build_state
from api.main import create_app
from datasets.synth.generator import generate_dataset
from docai.contracts.decision import DecisionOutcome
from docai.contracts.ledger import LedgerEntry
from docai.contracts.truth import TruthRecord
from docai.contracts.vendor import VendorMaster

ROOT = Path(__file__).resolve().parents[2]
SAMPLE_DIR = ROOT / "datasets" / "sample"


def _load_truths_from_dir(data_dir: Path) -> dict[UUID, TruthRecord]:
    manifest_path = data_dir / "manifest.json"
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        ids = [e["id"] for e in manifest["invoices"]]
    else:
        ids = [p.stem.removesuffix(".truth") for p in data_dir.glob("*.truth.json")]
    out: dict[UUID, TruthRecord] = {}
    for iid in ids:
        path = data_dir / f"{iid}.truth.json"
        if path.is_file():
            out[UUID(iid)] = TruthRecord.model_validate_json(path.read_text(encoding="utf-8"))
    return out


def _upload_all(client: TestClient, data_dir: Path) -> dict[str, UUID]:
    """Return map truth stem id -> persisted invoice_id from API."""
    mapping: dict[str, UUID] = {}
    manifest_path = data_dir / "manifest.json"
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        pdf_names = [f"{e['id']}.pdf" for e in manifest["invoices"]]
    else:
        pdf_names = sorted(p.name for p in data_dir.glob("*.pdf"))
    for name in pdf_names:
        pdf = data_dir / name
        if not pdf.is_file():
            continue
        resp = client.post(
            "/invoices",
            files={"file": (name, pdf.read_bytes(), "application/pdf")},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        mapping[pdf.stem] = UUID(body["invoice"]["invoice_id"])
    return mapping


@pytest.fixture
def e2e_client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[TestClient, dict[UUID, TruthRecord], dict[UUID, TruthRecord]]:
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    monkeypatch.setattr(deps, "UPLOAD_DIR", upload_dir)
    monkeypatch.setattr(main_mod, "UPLOAD_DIR", upload_dir)

    gen_dir = tmp_path / "generated"
    generate_dataset(12, 11, gen_dir)
    merged_master = tmp_path / "vendor_master.json"
    by_gstin: dict[str, object] = {}
    used_ids: set[str] = set()
    merged_vendors = []
    for path in (gen_dir / "vendor_master.json", SAMPLE_DIR / "vendor_master.json"):
        if not path.is_file():
            continue
        master = VendorMaster.model_validate_json(path.read_text(encoding="utf-8"))
        for v in master.vendors:
            key = v.gstin.upper()
            if key in by_gstin:
                continue
            vendor_id = v.vendor_id
            if vendor_id in used_ids:
                vendor_id = f"VX{len(used_ids):03d}"
            used_ids.add(vendor_id)
            merged_vendors.append(v.model_copy(update={"vendor_id": vendor_id}))
            by_gstin[key] = vendor_id
    merged = VendorMaster(vendors=merged_vendors)
    merged_master.write_text(merged.model_dump_json(indent=2), encoding="utf-8")

    state = build_state(
        database_url=f"sqlite:///{tmp_path / 'e2e.db'}",
        extract_fn=None,
        vendor_master_path=merged_master,
    )
    client = TestClient(create_app(state))

    gen_truths: dict[UUID, TruthRecord] = {}
    sample_truths: dict[UUID, TruthRecord] = {}
    for stem, api_id in _upload_all(client, gen_dir).items():
        truth = TruthRecord.model_validate_json(
            (gen_dir / f"{stem}.truth.json").read_text(encoding="utf-8")
        )
        gen_truths[api_id] = truth
    for stem, api_id in _upload_all(client, SAMPLE_DIR).items():
        truth = TruthRecord.model_validate_json(
            (SAMPLE_DIR / f"{stem}.truth.json").read_text(encoding="utf-8")
        )
        sample_truths[api_id] = truth
    return client, gen_truths, sample_truths


def _decision_match_rate(client: TestClient, truths: dict[UUID, TruthRecord]) -> tuple[int, int]:
    matched = 0
    for iid, truth in truths.items():
        resp = client.get(f"/invoices/{iid}")
        assert resp.status_code == 200
        body = resp.json()
        inv_ok = body["invoice"]["invoice_number"] == truth.invoice.invoice_number
        dec_ok = body["decision"]["outcome"] == truth.expected_decision.value
        if inv_ok and dec_ok:
            matched += 1
    return matched, len(truths)


def test_full_pipeline_offline_extract(
    e2e_client: tuple[TestClient, dict[UUID, TruthRecord], dict[UUID, TruthRecord]],
) -> None:
    client, gen_truths, sample_truths = e2e_client
    truths = {**gen_truths, **sample_truths}

    sample_matched, sample_total = _decision_match_rate(client, sample_truths)
    assert sample_matched == sample_total, (
        f"sample decision match {sample_matched}/{sample_total} (expected 100%)"
    )

    gen_matched, gen_total = _decision_match_rate(client, gen_truths)
    gen_rate = gen_matched / gen_total if gen_total else 0.0
    assert gen_rate >= 0.95, f"generated match rate {gen_rate:.2%} ({gen_matched}/{gen_total})"

    by_outcome: dict[str, list[UUID]] = {
        DecisionOutcome.ALLOW.value: [],
        DecisionOutcome.REVIEW.value: [],
        DecisionOutcome.BLOCK.value: [],
    }
    for iid, truth in truths.items():
        by_outcome[truth.expected_decision.value].append(iid)

    allow_id = by_outcome[DecisionOutcome.ALLOW.value][0]
    post = client.post(f"/invoices/{allow_id}/post")
    assert post.status_code == 200
    LedgerEntry.model_validate(post.json())
    again = client.post(f"/invoices/{allow_id}/post")
    assert again.status_code == 409
    assert again.json()["code"] == "already_posted"

    from docai.contracts.validation import IssueCode

    review_id = next(
        iid
        for iid, truth in truths.items()
        if IssueCode.MISSING_FIELD in truth.expected_issue_codes
        and truth.invoice.invoice_date is None
    )
    rev = client.post(
        f"/invoices/{review_id}/review",
        json={"action": "approve", "reviewer": "e2e", "corrections": None},
    )
    assert rev.status_code == 200
    assert rev.json()["decision"]["outcome"] == DecisionOutcome.ALLOW.value
    post_r = client.post(f"/invoices/{review_id}/post")
    assert post_r.status_code == 200, post_r.text

    block_id = by_outcome[DecisionOutcome.BLOCK.value][0]
    bad = client.post(
        f"/invoices/{block_id}/review",
        json={"action": "approve", "reviewer": "e2e"},
    )
    assert bad.status_code == 409

    q_all = client.get("/review-queue")
    assert q_all.status_code == 200
    q_review = client.get("/review-queue", params={"decision": ["REVIEW"]})
    assert q_review.status_code == 200
    assert all(item["outcome"] == "REVIEW" for item in q_review.json())

    file_resp = client.get(f"/invoices/{allow_id}/file")
    assert file_resp.status_code == 200
    assert file_resp.content[:4] == b"%PDF"
