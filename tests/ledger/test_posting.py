import uuid
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from datasets.synth.generator import generate_dataset
from db.repository import save_invoice, seed_vendors
from db.session import init_db, session_factory
from docai.contracts.vendor import VendorMaster
from docai.validate import build_history_from_manifest, decide, validate
from ledger.posting import post_invoice, verify_receipt_chain


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


def test_post_and_receipt_tamper(tmp_path) -> None:
    db_path = tmp_path / "ledger.db"
    engine = create_engine(f"sqlite:///{db_path}")
    init_db(engine)
    factory = session_factory(engine)
    data_dir = tmp_path / "data"
    with factory() as session:
        invoice_id = _seed_invoice(session, data_dir)

    with factory() as session:
        post_invoice(session, invoice_id, receipts_dir=tmp_path / "receipts")
        session.commit()
        assert verify_receipt_chain(session) is None

    tamper_path = tmp_path / "tamper.db"
    tamper_path.write_bytes(db_path.read_bytes())
    with create_engine(f"sqlite:///{tamper_path}").begin() as conn:
        conn.execute(text("DROP TRIGGER IF EXISTS ledger_entries_no_update"))
        conn.execute(
            text("UPDATE ledger_entries SET entry_hash = :h"),
            {"h": "0" * 64},
        )

    with create_engine(f"sqlite:///{tamper_path}").connect() as conn:
        from sqlalchemy.orm import Session as OrmSession

        with OrmSession(bind=conn) as session:
            assert verify_receipt_chain(session) == 1
