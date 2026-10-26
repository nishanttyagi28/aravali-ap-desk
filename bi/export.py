"""Export tidy CSV marts from the AP Desk database."""

from __future__ import annotations

import argparse
import csv
import json
import uuid
from collections.abc import Iterable
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from db.models import InvoiceRow, LedgerEntryRow, LedgerReceiptRow, VendorRow
from db.repository import latest_decision
from db.session import create_db_engine, init_db
from docai.contracts.extracted import ExtractedInvoice
from docai.contracts.validation import IssueCode, ValidationIssue
from ledger.receipt import money_str

INVOICE_COLUMNS = [
    "invoice_id",
    "vendor_id",
    "vendor_name",
    "vendor_gstin",
    "invoice_number",
    "invoice_date",
    "taxable_total",
    "cgst_total",
    "sgst_total",
    "igst_total",
    "cess_total",
    "grand_total",
    "decision",
    "top_issue_code",
    "issue_count",
    "posted",
    "posted_at",
]

LINE_COLUMNS = [
    "invoice_id",
    "line_index",
    "description",
    "hsn_sac",
    "qty",
    "unit_price",
    "gst_rate",
    "taxable_value",
    "cgst",
    "sgst",
    "igst",
    "cess",
    "total",
]

ISSUE_COLUMNS = ["invoice_id", "code", "severity", "field"]
LEDGER_COLUMNS = [
    "entry_id",
    "seq",
    "invoice_id",
    "vendor_id",
    "taxable_total",
    "cgst_total",
    "sgst_total",
    "igst_total",
    "cess_total",
    "grand_total",
    "posted_at",
    "receipt_sha256",
    "prev_receipt_sha256",
    "seal_provider",
    "seal_commit_id",
    "seal_manifest_sha256",
    "seal_witness_status",
]
VENDOR_COLUMNS = ["vendor_id", "legal_name", "gstin", "state_code", "pan", "bank_last4"]
EVAL_COLUMNS = ["metric", "field", "value", "run_id"]


def _resolve_db_url(arg: str) -> str:
    if "://" in arg:
        return arg
    return f"sqlite:///{Path(arg).resolve()}"


def _iso_date(value: date | None) -> str:
    return value.isoformat() if value else ""


def _iso_dt(value: datetime | None) -> str:
    return value.isoformat() if value else ""


def _top_issue(issues: list[ValidationIssue]) -> str:
    if not issues:
        return ""
    order = {IssueCode.GSTIN_CHECKSUM: 0, IssueCode.DUPLICATE_INVOICE: 1}
    ranked = sorted(issues, key=lambda i: (order.get(i.code, 99), i.code.value))
    return ranked[0].code.value


def _write_csv(path: Path, columns: list[str], rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in columns})


def _vendor_map(session: Session) -> dict[str, VendorRow]:
    return {v.vendor_id: v for v in session.scalars(select(VendorRow)).all()}


def _ledger_by_invoice(
    session: Session,
) -> dict[uuid.UUID, tuple[LedgerEntryRow, LedgerReceiptRow | None]]:
    entries = session.scalars(select(LedgerEntryRow)).all()
    receipts = {r.entry_id: r for r in session.scalars(select(LedgerReceiptRow)).all()}
    return {e.invoice_id: (e, receipts.get(e.entry_id)) for e in entries}


def export_marts(session: Session, out_dir: Path, eval_report: Path | None = None) -> None:
    vendors = _vendor_map(session)
    ledger_map = _ledger_by_invoice(session)
    invoice_rows: list[dict[str, Any]] = []
    line_rows: list[dict[str, Any]] = []
    issue_rows: list[dict[str, Any]] = []

    for inv_row in session.scalars(select(InvoiceRow).order_by(InvoiceRow.created_at)).all():
        invoice = ExtractedInvoice.model_validate(inv_row.payload)
        decision = latest_decision(session, inv_row.invoice_id)
        vendor = None
        if inv_row.invoice_id in ledger_map:
            vendor = vendors.get(ledger_map[inv_row.invoice_id][0].vendor_id)
        if vendor is None and invoice.vendor_gstin:
            vendor = next((v for v in vendors.values() if v.gstin == invoice.vendor_gstin), None)
        vendor_id = vendor.vendor_id if vendor else ""
        vendor_name = vendor.legal_name if vendor else ""
        posted_at = ""
        if inv_row.invoice_id in ledger_map:
            posted_at = _iso_dt(ledger_map[inv_row.invoice_id][0].posted_at)
        issues = decision.issues if decision else []
        invoice_rows.append(
            {
                "invoice_id": str(inv_row.invoice_id),
                "vendor_id": vendor_id,
                "vendor_name": vendor_name,
                "vendor_gstin": invoice.vendor_gstin or "",
                "invoice_number": invoice.invoice_number or "",
                "invoice_date": _iso_date(invoice.invoice_date),
                "taxable_total": money_str(invoice.taxable_total),
                "cgst_total": money_str(invoice.cgst_total),
                "sgst_total": money_str(invoice.sgst_total),
                "igst_total": money_str(invoice.igst_total),
                "cess_total": money_str(invoice.cess_total),
                "grand_total": money_str(invoice.grand_total),
                "decision": decision.outcome.value if decision else "",
                "top_issue_code": _top_issue(issues),
                "issue_count": str(len(issues)),
                "posted": "true" if inv_row.posted else "false",
                "posted_at": posted_at,
            }
        )
        for idx, line in enumerate(invoice.line_items):
            line_rows.append(
                {
                    "invoice_id": str(inv_row.invoice_id),
                    "line_index": str(idx),
                    "description": line.description,
                    "hsn_sac": line.hsn_sac or "",
                    "qty": money_str(line.qty),
                    "unit_price": money_str(line.unit_price),
                    "gst_rate": money_str(line.gst_rate),
                    "taxable_value": money_str(line.taxable_value),
                    "cgst": money_str(line.cgst),
                    "sgst": money_str(line.sgst),
                    "igst": money_str(line.igst),
                    "cess": money_str(line.cess),
                    "total": money_str(line.total),
                }
            )
        for issue in issues:
            issue_rows.append(
                {
                    "invoice_id": str(inv_row.invoice_id),
                    "code": issue.code.value,
                    "severity": issue.severity.value,
                    "field": issue.field or "",
                }
            )

    ledger_rows: list[dict[str, Any]] = []
    for receipt in session.scalars(select(LedgerReceiptRow).order_by(LedgerReceiptRow.seq)).all():
        entry = session.get(LedgerEntryRow, receipt.entry_id)
        if entry is None:
            continue
        seal = entry.seal_payload or {}
        ledger_rows.append(
            {
                "entry_id": str(entry.entry_id),
                "seq": str(receipt.seq),
                "invoice_id": str(entry.invoice_id),
                "vendor_id": entry.vendor_id,
                "taxable_total": money_str(Decimal(entry.taxable_total)),
                "cgst_total": money_str(Decimal(entry.cgst_total)),
                "sgst_total": money_str(Decimal(entry.sgst_total)),
                "igst_total": money_str(Decimal(entry.igst_total)),
                "cess_total": money_str(Decimal(entry.cess_total)),
                "grand_total": money_str(Decimal(entry.grand_total)),
                "posted_at": _iso_dt(entry.posted_at),
                "receipt_sha256": receipt.receipt_sha256,
                "prev_receipt_sha256": receipt.prev_receipt_sha256,
                "seal_provider": seal.get("provider", ""),
                "seal_commit_id": seal.get("commit_id", ""),
                "seal_manifest_sha256": seal.get("manifest_sha256", ""),
                "seal_witness_status": seal.get("witness_status", ""),
            }
        )

    vendor_rows = [
        {
            "vendor_id": v.vendor_id,
            "legal_name": v.legal_name,
            "gstin": v.gstin,
            "state_code": v.state_code,
            "pan": v.pan,
            "bank_last4": v.bank_last4 or "",
        }
        for v in sorted(vendors.values(), key=lambda x: x.vendor_id)
    ]

    _write_csv(out_dir / "invoices.csv", INVOICE_COLUMNS, invoice_rows)
    _write_csv(out_dir / "line_items.csv", LINE_COLUMNS, line_rows)
    _write_csv(out_dir / "issues.csv", ISSUE_COLUMNS, issue_rows)
    _write_csv(out_dir / "ledger.csv", LEDGER_COLUMNS, ledger_rows)
    _write_csv(out_dir / "vendors.csv", VENDOR_COLUMNS, vendor_rows)
    _write_eval_metrics(out_dir, eval_report)


def _write_eval_metrics(out_dir: Path, eval_report: Path | None) -> None:
    rows: list[dict[str, str]] = []
    if eval_report and eval_report.is_file():
        report = json.loads(eval_report.read_text(encoding="utf-8"))
        run_id = report.get("truth_dir", "run")
        summary = report.get("summary") or {}
        rows.append(
            {
                "metric": "header_macro_f1",
                "field": "",
                "value": str(summary.get("header_macro_f1") or ""),
                "run_id": str(run_id),
            }
        )
        rows.append(
            {
                "metric": "decision_accuracy",
                "field": "",
                "value": str(summary.get("decision_accuracy") or ""),
                "run_id": str(run_id),
            }
        )
        line = summary.get("line_items") or {}
        rows.append(
            {
                "metric": "line_items_f1",
                "field": "",
                "value": str(line.get("f1") or ""),
                "run_id": str(run_id),
            }
        )
        bboxes = summary.get("bboxes") or {}
        rows.append(
            {
                "metric": "bbox_iou_at_0_5",
                "field": "",
                "value": str(bboxes.get("iou_at_0_5_rate") or ""),
                "run_id": str(run_id),
            }
        )
        for name, scores in (summary.get("header_fields") or {}).items():
            rows.append(
                {
                    "metric": "header_field_f1",
                    "field": name,
                    "value": str(scores.get("f1") or ""),
                    "run_id": str(run_id),
                }
            )
    _write_csv(out_dir / "eval_metrics.csv", EVAL_COLUMNS, rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export BI CSV marts")
    parser.add_argument("--db", required=True, help="SQLite path or SQLAlchemy URL")
    parser.add_argument("--out", type=Path, required=True, help="Output directory for CSV files")
    parser.add_argument("--eval-report", type=Path, default=None, help="Optional eval report JSON")
    args = parser.parse_args(argv)

    engine = create_db_engine(_resolve_db_url(args.db))
    init_db(engine)
    with Session(engine) as session:
        export_marts(session, args.out, args.eval_report)
    print(f"Exported CSV marts to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
