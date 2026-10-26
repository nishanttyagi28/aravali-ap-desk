import uuid
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from datasets.synth.generator import generate_dataset
from db.repository import save_invoice, seed_vendors
from db.session import init_db, session_factory
from docai.contracts.vendor import VendorMaster
from docai.validate import build_history_from_manifest, decide, validate
from ledger.posting import post_invoice, verify_chain
from ledger.seal import StubSealProvider


def _seed_invoice(session: Session, tmp_path: Path) -> uuid.UUID:
    generate_dataset(1, 1, tmp_path, cases_override=["clean_intrastate"])
    master = VendorMaster.model_validate_json((tmp_path / "vendor_master.json").read_text())
    seed_vendors(session, master)
    truth_path = next(tmp_path.glob("*.truth.json"))
    from docai.contracts.truth import TruthRecord

    truth = TruthRecord.model_validate_json(truth_path.read_text(encoding="utf-8"))
    history = build_history_from_manifest([])
    issues = validate(truth.invoice, master, history)
    decision = decide(issues, truth.invoice)
    pdf = tmp_path / f"{truth.invoice.invoice_id}.pdf"
    save_invoice(session, truth.invoice, decision, pdf)
    session.commit()
    return truth.invoice.invoice_id


def test_post_and_witness_tamper(tmp_path) -> None:
    db_path = tmp_path / "ledger.db"
    engine = create_engine(f"sqlite:///{db_path}")
    init_db(engine)
    factory = session_factory(engine)
    data_dir = tmp_path / "data"
    with factory() as session:
        invoice_id = _seed_invoice(session, data_dir)

    with factory() as session:
        post_invoice(session, invoice_id)
        session.commit()
        assert verify_chain(session) == "match"

    tamper_path = tmp_path / "tamper.db"
    tamper_path.write_bytes(db_path.read_bytes())
    tamper_engine = create_engine(f"sqlite:///{tamper_path}")
    with tamper_engine.begin() as conn:
        conn.execute(text("DROP TRIGGER IF EXISTS ledger_entries_no_update"))
        conn.execute(text("DROP TRIGGER IF EXISTS ledger_entries_no_delete"))
        conn.execute(
            text("UPDATE ledger_entries SET entry_hash = :h"),
            {"h": "0" * 64},
        )

    with create_engine(f"sqlite:///{tamper_path}").connect() as conn:
        row = conn.execute(
            text("SELECT entry_hash, seal_payload, chain_prev_hash FROM ledger_entries")
        ).first()
        provider = StubSealProvider()
        seal = row[1]
        if isinstance(seal, str):
            import json

            seal = json.loads(seal)
        manifest_sha = seal["manifest_sha256"]
        assert row[0] == "0" * 64
        assert provider.witness(row[0], manifest_sha, row[2]) == "mismatch"
