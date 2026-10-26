"""Build deterministic demo DB + CSV marts through the real pipeline."""

from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from pathlib import Path

from sqlalchemy.orm import Session

from bi.export import export_marts
from bi.mis import build_mis_workbook
from datasets.synth.generator import generate_dataset
from db.repository import save_invoice, seed_vendors
from db.session import create_db_engine, init_db, session_factory
from docai.contracts.decision import DecisionOutcome
from docai.contracts.truth import TruthRecord
from docai.contracts.vendor import VendorMaster
from docai.extract import extract_file
from docai.validate import build_history_from_manifest, decide, validate
from evals.metrics import compute_report, write_report
from ledger.posting import post_invoice


def _run_pipeline(
    session: Session,
    truth_dir: Path,
    receipts_dir: Path,
) -> Path:
    manifest = json.loads((truth_dir / "manifest.json").read_text(encoding="utf-8"))
    master = VendorMaster.model_validate_json((truth_dir / "vendor_master.json").read_text())
    seed_vendors(session, master)
    seen: list = []
    for entry in manifest["invoices"]:
        TruthRecord.model_validate_json(
            (truth_dir / f"{entry['id']}.truth.json").read_text(encoding="utf-8")
        )
        pdf = truth_dir / f"{entry['id']}.pdf"
        invoice = extract_file(pdf)
        history = build_history_from_manifest(seen)
        issues = validate(invoice, master, history)
        decision = decide(issues, invoice)
        save_invoice(session, invoice, decision, pdf)
        seen.append((invoice, None))
        if decision.outcome == DecisionOutcome.ALLOW:
            post_invoice(session, invoice.invoice_id, receipts_dir=receipts_dir)
    session.commit()
    report_path = truth_dir / "eval_report.json"
    report = compute_report("truth", truth_dir)
    write_report(report, report_path)
    return report_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build demo BI marts (n=50, seed=7)")
    parser.add_argument("--out", type=Path, default=Path("bi/data"), help="Output directory")
    parser.add_argument("--n", type=int, default=50)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args(argv)

    out_dir = args.out
    out_dir.mkdir(parents=True, exist_ok=True)
    db_path = out_dir / "demo.db"
    receipts_dir = out_dir / "receipts"
    if db_path.is_file():
        db_path.unlink()
    if receipts_dir.is_dir():
        shutil.rmtree(receipts_dir)

    with tempfile.TemporaryDirectory(dir=out_dir.parent) as tmp:
        synth_dir = Path(tmp) / "synth"
        generate_dataset(args.n, args.seed, synth_dir)
        engine = create_db_engine(f"sqlite:///{db_path}")
        init_db(engine)
        factory = session_factory(engine)
        with factory() as session:
            report_path = _run_pipeline(session, synth_dir, receipts_dir)

        export_marts(Session(engine), out_dir, report_path)
        build_mis_workbook(out_dir, out_dir / "mis.xlsx")

    print(f"Demo DB: {db_path}")
    print(f"CSV marts: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
