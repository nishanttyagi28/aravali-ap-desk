import csv
from pathlib import Path

from sqlalchemy.orm import Session

from bi.demo import main as demo_main
from bi.export import INVOICE_COLUMNS, export_marts
from db.session import create_db_engine, init_db


def test_demo_export_columns_and_lf(tmp_path: Path) -> None:
    out = tmp_path / "bi_data"
    rc = demo_main(["--out", str(out), "--n", "5", "--seed", "7"])
    assert rc == 0
    inv_path = out / "invoices.csv"
    assert inv_path.is_file()
    text = inv_path.read_text(encoding="utf-8")
    assert "\r\n" not in text
    with inv_path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        assert reader.fieldnames == INVOICE_COLUMNS
        rows = list(reader)
    assert len(rows) == 5
    for name in (
        "line_items.csv",
        "issues.csv",
        "ledger.csv",
        "vendors.csv",
        "eval_metrics.csv",
        "mis.xlsx",
    ):
        assert (out / name).is_file()


def test_export_round_trip(tmp_path: Path) -> None:
    out = tmp_path / "mart"
    demo_main(["--out", str(tmp_path / "src"), "--n", "3", "--seed", "1"])
    db = tmp_path / "src" / "demo.db"
    engine = create_db_engine(f"sqlite:///{db}")
    init_db(engine)
    with Session(engine) as session:
        export_marts(session, out, tmp_path / "src" / "eval_report.json")
    assert (out / "invoices.csv").is_file()
