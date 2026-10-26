"""Business logic for HTTP handlers."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from db.models import InvoiceRow, LedgerEntryRow
from db.repository import (
    audit,
    get_extracted,
    get_invoice_row,
    latest_decision,
    list_invoices_ordered,
    load_vendor_master,
    record_review_action,
    save_invoice,
    seed_vendors,
)
from docai.contracts.decision import DecidedBy, Decision, DecisionOutcome
from docai.contracts.extracted import ExtractedInvoice
from docai.contracts.metrics import Metrics
from docai.contracts.review import ReviewAction, ReviewActionType, ReviewQueueItem, ReviewResult
from docai.contracts.validation import IssueCode
from docai.contracts.vendor import VendorMaster
from docai.validate import build_history_from_manifest, decide, validate
from docai.validate.policy import BLOCK_CODES
from ledger.posting import AlreadyPosted, NotPostable, post_invoice

DEFAULT_VENDOR_MASTER = Path("data/vendor_master.json")


def ensure_vendors(session: Session, master_path: Path | None) -> VendorMaster:
    path = master_path or DEFAULT_VENDOR_MASTER
    if path.is_file():
        master = VendorMaster.model_validate_json(path.read_text(encoding="utf-8"))
        seed_vendors(session, master)
    return load_vendor_master(session)


def run_validation(
    session: Session,
    inv: ExtractedInvoice,
    master: VendorMaster,
    *,
    duplicate_of: UUID | None = None,
) -> Decision:
    prior = [r for r in list_invoices_ordered(session) if r.invoice_id != inv.invoice_id]
    history = build_history_from_manifest(
        [(ExtractedInvoice.model_validate(r.payload), None) for r in prior]
    )
    issues = validate(inv, master, history, duplicate_of=duplicate_of)
    return decide(issues, inv)


def ingest_upload(
    session: Session,
    content: bytes,
    filename: str,
    extract_fn,
    master: VendorMaster,
    upload_dir: Path,
) -> tuple[ExtractedInvoice, Decision]:
    digest = hashlib.sha256(content).hexdigest()
    dest = upload_dir / f"{digest}.pdf"
    if not dest.exists():
        dest.write_bytes(content)
    invoice = extract_fn(dest)
    if not isinstance(invoice, ExtractedInvoice):
        invoice = ExtractedInvoice.model_validate(invoice)
    invoice = invoice.model_copy(update={"sha256": digest, "source_file": filename or dest.name})
    decision = run_validation(session, invoice, master)
    save_invoice(session, invoice, decision, dest)
    audit(session, "upload", "Invoice uploaded", invoice_id=invoice.invoice_id)
    return invoice, decision


def apply_review(
    session: Session,
    invoice_id: UUID,
    action: ReviewAction,
    master: VendorMaster,
) -> ReviewResult:
    row = get_invoice_row(session, invoice_id)
    if row is None:
        raise KeyError("not_found")
    record_review_action(session, invoice_id, action)
    inv = get_extracted(session, invoice_id)
    if inv is None:
        raise KeyError("not_found")

    if action.action == ReviewActionType.CORRECT and action.corrections:
        data = inv.model_dump(mode="python")
        data = _deep_merge(data, action.corrections)
        inv = ExtractedInvoice.model_validate(data)

    prior = [r for r in list_invoices_ordered(session) if r.invoice_id != invoice_id]
    history = build_history_from_manifest(
        [(ExtractedInvoice.model_validate(r.payload), None) for r in prior]
    )
    issues = validate(inv, master, history)
    decided_by = DecidedBy.HUMAN
    decided_at = datetime.now(UTC)

    if action.action == ReviewActionType.REJECT:
        outcome = DecisionOutcome.BLOCK
    elif action.action == ReviewActionType.APPROVE:
        if any(issue.code in BLOCK_CODES for issue in issues):
            raise ValueError("block_conflict")
        outcome = DecisionOutcome.ALLOW
        row.human_approved = True
    elif action.action == ReviewActionType.CORRECT:
        if any(issue.code in BLOCK_CODES for issue in issues):
            outcome = DecisionOutcome.BLOCK
        elif issues:
            outcome = DecisionOutcome.REVIEW
        else:
            outcome = DecisionOutcome.ALLOW
            row.human_approved = True
    else:
        outcome = decide(issues, inv).outcome

    decision = Decision(
        invoice_id=invoice_id,
        outcome=outcome,
        issues=issues,
        reasons=[i.message for i in issues] if issues else ["Review complete"],
        decided_by=decided_by,
        decided_at=decided_at,
    )
    save_invoice(session, inv, decision, Path(row.file_path))
    return ReviewResult(decision=decision, invoice=inv)


def review_queue(
    session: Session,
    master: VendorMaster,
    decisions: list[DecisionOutcome] | None,
    issue_codes: list[IssueCode] | None,
) -> list[ReviewQueueItem]:
    items: list[ReviewQueueItem] = []
    for row in list_invoices_ordered(session):
        decision = latest_decision(session, row.invoice_id)
        if decision is None:
            continue
        if decisions and decision.outcome not in decisions:
            continue
        if issue_codes and not any(i.code in issue_codes for i in decision.issues):
            continue
        inv = ExtractedInvoice.model_validate(row.payload)
        vendor = master.lookup_by_gstin(inv.vendor_gstin or "")
        top = decision.issues[0].code if decision.issues else None
        items.append(
            ReviewQueueItem(
                invoice_id=row.invoice_id,
                vendor_name=vendor.legal_name if vendor else None,
                vendor_gstin=inv.vendor_gstin,
                invoice_number=inv.invoice_number,
                invoice_date=inv.invoice_date,
                grand_total=inv.grand_total,
                outcome=decision.outcome,
                top_issue_code=top,
                issue_count=len(decision.issues),
                posted=row.posted,
            )
        )
    return items


def compute_metrics(session: Session) -> Metrics:
    invoices = session.scalar(select(func.count()).select_from(InvoiceRow)) or 0
    posted = session.scalar(select(func.count()).select_from(LedgerEntryRow)) or 0
    allow = review = block = 0
    queue_depth = 0
    for row in list_invoices_ordered(session):
        decision = latest_decision(session, row.invoice_id)
        if decision is None:
            continue
        if decision.outcome == DecisionOutcome.ALLOW:
            allow += 1
        elif decision.outcome == DecisionOutcome.REVIEW:
            review += 1
            if not row.posted:
                queue_depth += 1
        elif decision.outcome == DecisionOutcome.BLOCK:
            block += 1
    return Metrics(
        invoices_processed=invoices,
        allow_count=allow,
        review_count=review,
        block_count=block,
        posted_count=posted,
        queue_depth=queue_depth,
    )


def _deep_merge(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


__all__ = [
    "AlreadyPosted",
    "NotPostable",
    "apply_review",
    "compute_metrics",
    "ensure_vendors",
    "ingest_upload",
    "post_invoice",
    "review_queue",
    "run_validation",
]
