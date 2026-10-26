"""Excel MIS workbook from exported CSV marts."""

from __future__ import annotations

import csv
from pathlib import Path

from openpyxl import Workbook

MIS_SHEETS = (
    "Invoices",
    "LineItems",
    "Issues",
    "Ledger",
    "Vendors",
    "EvalMetrics",
)

_CSV_MAP = {
    "Invoices": "invoices.csv",
    "LineItems": "line_items.csv",
    "Issues": "issues.csv",
    "Ledger": "ledger.csv",
    "Vendors": "vendors.csv",
    "EvalMetrics": "eval_metrics.csv",
}


def build_mis_workbook(data_dir: Path, out_path: Path) -> None:
    wb = Workbook()
    default = wb.active
    wb.remove(default)
    for sheet_name in MIS_SHEETS:
        ws = wb.create_sheet(sheet_name)
        csv_path = data_dir / _CSV_MAP[sheet_name]
        if not csv_path.is_file():
            continue
        with csv_path.open(encoding="utf-8", newline="") as fh:
            reader = csv.reader(fh)
            for row in reader:
                ws.append(row)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out_path)
