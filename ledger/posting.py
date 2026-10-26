"""Ledger posting with hash-chained KarmaSakshi-style stub receipts."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from db.models import InvoiceRow, LedgerEntryRow, LedgerReceiptRow
from db.repository import audit, get_extracted, ledger_entry_for_invoice, load_vendor_master
from docai.contracts.decision import DecisionOutcome
from docai.contracts.ledger import LedgerEntry
from ledger.receipt import (
    GENESIS_PREV_RECEIPT_SHA256,
    amounts_dict,
    build_receipt_body,
    receipt_sha256,
)
from ledger.seal import StubSealProvider


class AlreadyPosted(Exception):
    """Invoice was already posted to the ledger."""


class NotPostable(Exception):
    """Invoice decision does not allow posting."""


class InvoiceNotFound(Exception):
    pass


def _latest_receipt_hash(session: Session) -> str:
    row = session.scalars(
        select(LedgerReceiptRow).order_by(LedgerReceiptRow.seq.desc()).limit(1)
    ).first()
    return row.receipt_sha256 if row else GENESIS_PREV_RECEIPT_SHA256


def _next_seq(session: Session) -> int:
    current = session.scalar(select(func.max(LedgerReceiptRow.seq))) or 0
    return current + 1


def _write_receipt_file(receipts_dir: Path, seq: int, body: dict, digest: str) -> None:
    receipts_dir.mkdir(parents=True, exist_ok=True)
    payload = {"receipt_sha256": digest, **body}
    path = receipts_dir / f"{seq}.json"
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


def post_invoice(
    session: Session,
    invoice_id: uuid.UUID,
    *,
    receipts_dir: Path | None = None,
) -> LedgerEntry:
    row = session.get(InvoiceRow, invoice_id)
    if row is None:
        raise InvoiceNotFound(str(invoice_id))
    if ledger_entry_for_invoice(session, invoice_id) is not None:
        raise AlreadyPosted(str(invoice_id))

    from db.repository import latest_decision

    decision = latest_decision(session, invoice_id)
    if decision is None:
        raise NotPostable("missing decision")
    allowed = decision.outcome == DecisionOutcome.ALLOW or (
        decision.outcome == DecisionOutcome.REVIEW and row.human_approved
    )
    if not allowed:
        raise NotPostable(decision.outcome.value)

    invoice = get_extracted(session, invoice_id)
    if invoice is None:
        raise InvoiceNotFound(str(invoice_id))

    master = load_vendor_master(session)
    vendor = master.lookup_by_gstin(invoice.vendor_gstin or "")
    if vendor is None:
        raise NotPostable("unknown vendor")
    vendor_id = vendor.vendor_id

    posted_at = datetime.now(UTC)
    entry_id = uuid.uuid4()
    prev_receipt = _latest_receipt_hash(session)
    seq = _next_seq(session)
    body = build_receipt_body(
        entry_id=entry_id,
        invoice_id=invoice_id,
        vendor_id=vendor_id,
        taxable_total=invoice.taxable_total,
        cgst_total=invoice.cgst_total,
        sgst_total=invoice.sgst_total,
        igst_total=invoice.igst_total,
        cess_total=invoice.cess_total,
        grand_total=invoice.grand_total,
        posted_at=posted_at,
        prev_receipt_sha256=prev_receipt,
        seq=seq,
    )
    digest = receipt_sha256(body)
    provider = StubSealProvider()
    seal = provider.seal_receipt(digest)

    session.add(
        LedgerEntryRow(
            entry_id=entry_id,
            invoice_id=invoice_id,
            vendor_id=vendor_id,
            taxable_total=str(invoice.taxable_total),
            cgst_total=str(invoice.cgst_total),
            sgst_total=str(invoice.sgst_total),
            igst_total=str(invoice.igst_total),
            cess_total=str(invoice.cess_total),
            grand_total=str(invoice.grand_total),
            posted_at=posted_at,
            seal_payload=seal.model_dump(mode="json"),
            chain_prev_hash=prev_receipt,
            entry_hash=digest,
        )
    )
    session.flush()
    session.add(
        LedgerReceiptRow(
            entry_id=entry_id,
            receipt_sha256=digest,
            prev_receipt_sha256=prev_receipt,
            body=body,
        )
    )
    row.posted = True
    audit(session, "ledger_post", "Invoice posted", invoice_id=invoice_id)
    session.flush()

    out_dir = receipts_dir if receipts_dir is not None else Path("data/receipts")
    _write_receipt_file(out_dir, seq, body, digest)

    return LedgerEntry(
        entry_id=entry_id,
        invoice_id=invoice_id,
        vendor_id=vendor_id,
        taxable_total=invoice.taxable_total,
        cgst_total=invoice.cgst_total,
        sgst_total=invoice.sgst_total,
        igst_total=invoice.igst_total,
        cess_total=invoice.cess_total,
        grand_total=invoice.grand_total,
        posted_at=posted_at,
        seal=seal,
    )


def _posted_at_matches(stored: datetime, body_value: str | None) -> bool:
    if not body_value:
        return False
    if stored.isoformat() == body_value:
        return True
    if stored.tzinfo is not None and stored.astimezone(UTC).isoformat() == body_value:
        return True
    naive = stored.replace(tzinfo=None).isoformat()
    return naive == body_value.replace("+00:00", "").replace("Z", "")


def _entry_matches_receipt_body(entry: LedgerEntryRow, body: dict) -> bool:
    from decimal import Decimal

    if str(entry.entry_id) != body.get("entry_id"):
        return False
    if str(entry.invoice_id) != body.get("invoice_id"):
        return False
    if entry.vendor_id != body.get("vendor_id"):
        return False
    if not _posted_at_matches(entry.posted_at, body.get("posted_at")):
        return False
    expected_amounts = amounts_dict(
        taxable_total=Decimal(entry.taxable_total),
        cgst_total=Decimal(entry.cgst_total),
        sgst_total=Decimal(entry.sgst_total),
        igst_total=Decimal(entry.igst_total),
        cess_total=Decimal(entry.cess_total),
        grand_total=Decimal(entry.grand_total),
    )
    return expected_amounts == body.get("amounts")


def verify_receipt_chain(session: Session) -> int | None:
    """Return the first broken ``seq``, or ``None`` if the chain is intact."""
    rows = list(session.scalars(select(LedgerReceiptRow).order_by(LedgerReceiptRow.seq)).all())
    expected_prev = GENESIS_PREV_RECEIPT_SHA256
    expected_seq = 1
    for row in rows:
        if row.seq != expected_seq:
            return row.seq
        expected_seq += 1
        if row.seq <= 0:
            return row.seq or 1
        if row.body.get("seq") != row.seq:
            return row.seq
        if row.prev_receipt_sha256 != expected_prev:
            return row.seq
        digest = receipt_sha256(row.body)
        if digest != row.receipt_sha256:
            return row.seq
        entry = session.get(LedgerEntryRow, row.entry_id)
        if entry is None or entry.entry_hash != row.receipt_sha256:
            return row.seq
        if not _entry_matches_receipt_body(entry, row.body):
            return row.seq
        seal_sha = (entry.seal_payload or {}).get("manifest_sha256")
        if seal_sha != row.receipt_sha256:
            return row.seq
        expected_prev = row.receipt_sha256
    return None


def verify_chain(session: Session) -> str:
    broken = verify_receipt_chain(session)
    return "match" if broken is None else "mismatch"
