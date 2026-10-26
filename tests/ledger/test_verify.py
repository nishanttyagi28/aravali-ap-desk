import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from api.deps import build_state
from api.main import create_app
from datasets.synth.generator import generate_dataset
from db.repository import save_invoice, seed_vendors
from db.session import init_db, session_factory
from docai.contracts.truth import TruthRecord
from docai.contracts.vendor import VendorMaster
from docai.validate import build_history_from_manifest, decide, validate
from ledger.posting import post_invoice, verify_receipt_chain
from ledger.verify import main as verify_main


def _seed_many(session: Session, tmp_path: Path, n: int) -> list[uuid.UUID]:
    generate_dataset(n, 3, tmp_path, cases_override=["clean_intrastate"] * n)
    master = VendorMaster.model_validate_json((tmp_path / "vendor_master.json").read_text())
    seed_vendors(session, master)
    ids: list[uuid.UUID] = []
    seen = []
    for truth_path in sorted(tmp_path.glob("*.truth.json")):
        truth = TruthRecord.model_validate_json(truth_path.read_text(encoding="utf-8"))
        history = build_history_from_manifest(seen)
        issues = validate(truth.invoice, master, history)
        decision = decide(issues, truth.invoice)
        pdf = tmp_path / f"{truth.invoice.invoice_id}.pdf"
        save_invoice(session, truth.invoice, decision, pdf)
        seen.append((truth.invoice, None))
        ids.append(truth.invoice.invoice_id)
    session.commit()
    return ids


def test_receipt_chain_n_posts_verify(tmp_path: Path) -> None:
    db_path = tmp_path / "chain.db"
    engine = create_engine(f"sqlite:///{db_path}")
    init_db(engine)
    factory = session_factory(engine)
    data_dir = tmp_path / "data"
    with factory() as session:
        ids = _seed_many(session, data_dir, 4)
    with factory() as session:
        for iid in ids:
            post_invoice(session, iid, receipts_dir=tmp_path / "receipts")
        session.commit()
        assert verify_receipt_chain(session) is None


@pytest.mark.parametrize(
    "mutation_sql",
    [
        "UPDATE ledger_entries SET taxable_total = '0.00' WHERE entry_id = :eid",
        "UPDATE ledger_receipts SET prev_receipt_sha256 = :zeros WHERE seq = 1",
        "UPDATE ledger_receipts SET seq = 99 WHERE seq = 1",
    ],
)
def test_verify_fails_on_tamper(tmp_path: Path, mutation_sql: str) -> None:
    db_path = tmp_path / "tamper.db"
    engine = create_engine(f"sqlite:///{db_path}")
    init_db(engine)
    factory = session_factory(engine)
    data_dir = tmp_path / "data"
    with factory() as session:
        ids = _seed_many(session, data_dir, 2)
    with factory() as session:
        post_invoice(session, ids[0], receipts_dir=tmp_path / "receipts")
        session.commit()
    with engine.begin() as conn:
        conn.execute(text("DROP TRIGGER IF EXISTS ledger_entries_no_update"))
        conn.execute(text("DROP TRIGGER IF EXISTS ledger_receipts_no_update"))
        conn.execute(text("DROP TRIGGER IF EXISTS ledger_receipts_no_delete"))
        row = conn.execute(text("SELECT entry_id FROM ledger_entries LIMIT 1")).first()
        eid = str(row[0])
        params = {"eid": eid, "zeros": "f" * 64}
        conn.execute(text(mutation_sql), params)

    with factory() as session:
        broken = verify_receipt_chain(session)
        assert broken is not None

    rc = verify_main(["--db", str(db_path)])
    assert rc == 1


def test_verify_fails_on_deleted_receipt(tmp_path: Path) -> None:
    db_path = tmp_path / "del.db"
    engine = create_engine(f"sqlite:///{db_path}")
    init_db(engine)
    factory = session_factory(engine)
    data_dir = tmp_path / "data"
    with factory() as session:
        ids = _seed_many(session, data_dir, 2)
    with factory() as session:
        post_invoice(session, ids[0], receipts_dir=tmp_path / "receipts")
        post_invoice(session, ids[1], receipts_dir=tmp_path / "receipts")
        session.commit()
    with engine.begin() as conn:
        conn.execute(text("DROP TRIGGER IF EXISTS ledger_receipts_no_delete"))
        conn.execute(text("DELETE FROM ledger_receipts WHERE seq = 1"))
    with factory() as session:
        assert verify_receipt_chain(session) == 2


def test_api_post_returns_seal(tmp_path: Path) -> None:
    generate_dataset(1, 9, tmp_path, cases_override=["clean_intrastate"])
    master_path = tmp_path / "vendor_master.json"
    state = build_state(
        database_url=f"sqlite:///{tmp_path / 'api.db'}",
        vendor_master_path=master_path,
    )
    client = TestClient(create_app(state))
    pdf = next(tmp_path.glob("*.pdf"))
    up = client.post("/invoices", files={"file": (pdf.name, pdf.read_bytes(), "application/pdf")})
    assert up.status_code == 200
    inv_id = up.json()["invoice"]["invoice_id"]
    post = client.post(f"/invoices/{inv_id}/post")
    assert post.status_code == 200
    seal = post.json()["seal"]
    assert seal["provider"] == "stub"
    assert seal["witness_status"] == "local"
    assert len(seal["commit_id"]) == 64
    assert seal["commit_id"] == seal["manifest_sha256"]
