"""High-level persistence helpers for API and ledger."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from db.models import (
    AuditLogRow,
    DecisionRow,
    InvoiceRow,
    LedgerEntryRow,
    ReviewActionRow,
    VendorRow,
)
from docai.contracts.decision import Decision
from docai.contracts.extracted import ExtractedInvoice
from docai.contracts.review import ReviewAction
from docai.contracts.vendor import Vendor, VendorMaster


def load_vendor_master(session: Session) -> VendorMaster:
    rows = session.scalars(select(VendorRow)).all()
    return VendorMaster(
        vendors=[
            Vendor(
                vendor_id=r.vendor_id,
                legal_name=r.legal_name,
                gstin=r.gstin,
                state_code=r.state_code,
                pan=r.pan,
                bank_last4=r.bank_last4,
            )
            for r in rows
        ]
    )


def seed_vendors(session: Session, master: VendorMaster) -> None:
    if session.scalars(select(VendorRow).limit(1)).first():
        return
    for vendor in master.vendors:
        session.add(
            VendorRow(
                vendor_id=vendor.vendor_id,
                legal_name=vendor.legal_name,
                gstin=vendor.gstin,
                state_code=vendor.state_code,
                pan=vendor.pan,
                bank_last4=vendor.bank_last4,
            )
        )
    session.flush()


def list_invoices_ordered(session: Session) -> list[InvoiceRow]:
    return list(session.scalars(select(InvoiceRow).order_by(InvoiceRow.created_at)).all())


def save_invoice(
    session: Session,
    invoice: ExtractedInvoice,
    decision: Decision,
    file_path: Path,
) -> None:
    row = session.get(InvoiceRow, invoice.invoice_id)
    payload = json.loads(invoice.model_dump_json())
    decision_payload = json.loads(decision.model_dump_json())
    if row is None:
        row = InvoiceRow(
            invoice_id=invoice.invoice_id,
            sha256=invoice.sha256,
            source_file=invoice.source_file,
            file_path=str(file_path),
            payload=payload,
            vendor_gstin=invoice.vendor_gstin,
            invoice_number=invoice.invoice_number,
            posted=False,
            human_approved=False,
        )
        session.add(row)
    else:
        row.payload = payload
        row.vendor_gstin = invoice.vendor_gstin
        row.invoice_number = invoice.invoice_number
        row.sha256 = invoice.sha256
        row.source_file = invoice.source_file
        row.file_path = str(file_path)
    session.add(
        DecisionRow(
            invoice_id=invoice.invoice_id,
            outcome=decision.outcome.value,
            decided_by=decision.decided_by.value,
            decided_at=decision.decided_at,
            payload=decision_payload,
        )
    )
    session.flush()


def latest_decision(session: Session, invoice_id: uuid.UUID) -> Decision | None:
    stmt = (
        select(DecisionRow)
        .where(DecisionRow.invoice_id == invoice_id)
        .order_by(DecisionRow.id.desc())
        .limit(1)
    )
    row = session.scalars(stmt).first()
    if row is None:
        return None
    return Decision.model_validate(row.payload)


def get_invoice_row(session: Session, invoice_id: uuid.UUID) -> InvoiceRow | None:
    return session.get(InvoiceRow, invoice_id)


def get_extracted(session: Session, invoice_id: uuid.UUID) -> ExtractedInvoice | None:
    row = get_invoice_row(session, invoice_id)
    if row is None:
        return None
    return ExtractedInvoice.model_validate(row.payload)


def record_review_action(session: Session, invoice_id: uuid.UUID, action: ReviewAction) -> None:
    session.add(
        ReviewActionRow(
            invoice_id=invoice_id,
            action=action.action.value,
            reviewer=action.reviewer,
            corrections=action.corrections,
        )
    )


def audit(session: Session, event_type: str, message: str, **detail: Any) -> None:
    invoice_id = detail.get("invoice_id")
    serialisable = {k: str(v) if isinstance(v, uuid.UUID) else v for k, v in detail.items()}
    session.add(
        AuditLogRow(
            event_type=event_type,
            invoice_id=invoice_id,
            detail=serialisable or None,
            message=message,
        )
    )


def ledger_entry_for_invoice(session: Session, invoice_id: uuid.UUID) -> LedgerEntryRow | None:
    return session.scalars(
        select(LedgerEntryRow).where(LedgerEntryRow.invoice_id == invoice_id)
    ).first()
