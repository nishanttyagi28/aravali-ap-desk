"""Ledger posting with hash-chained stub seals."""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from db.models import InvoiceRow, LedgerEntryRow
from db.repository import audit, get_extracted, ledger_entry_for_invoice, load_vendor_master
from docai.contracts.decision import DecisionOutcome
from docai.contracts.ledger import LedgerEntry, SealRef, WitnessStatus
from docai.contracts.ledger import SealProvider as SealProviderKind
from ledger.seal import StubSealProvider


class AlreadyPosted(Exception):
    """Invoice was already posted to the ledger."""


class NotPostable(Exception):
    """Invoice decision does not allow posting."""


class InvoiceNotFound(Exception):
    pass


def _latest_chain_hash(session: Session) -> str | None:
    row = session.scalars(
        select(LedgerEntryRow).order_by(LedgerEntryRow.posted_at.desc()).limit(1)
    ).first()
    return row.entry_hash if row else None


def post_invoice(session: Session, invoice_id: uuid.UUID) -> LedgerEntry:
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
    manifest = {
        "invoice_id": str(invoice_id),
        "vendor_id": vendor_id,
        "taxable_total": str(invoice.taxable_total),
        "cgst_total": str(invoice.cgst_total),
        "sgst_total": str(invoice.sgst_total),
        "igst_total": str(invoice.igst_total),
        "cess_total": str(invoice.cess_total),
        "grand_total": str(invoice.grand_total),
        "posted_at": posted_at.isoformat(),
    }
    provider = StubSealProvider()
    seal = provider.seal(manifest)
    chain_prev = _latest_chain_hash(session)
    entry_hash = hashlib.sha256(f"{chain_prev or ''}|{seal.manifest_sha256}".encode()).hexdigest()

    entry_id = uuid.uuid4()
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
            chain_prev_hash=chain_prev,
            entry_hash=entry_hash,
        )
    )
    row.posted = True
    audit(session, "ledger_post", "Invoice posted", invoice_id=invoice_id)
    session.flush()

    witnessed = provider.witness(entry_hash, seal.manifest_sha256, chain_prev)
    witness_status = WitnessStatus.WITNESSED if witnessed == "match" else WitnessStatus.FAILED
    seal = SealRef(
        provider=SealProviderKind.STUB,
        commit_id=seal.commit_id,
        manifest_sha256=seal.manifest_sha256,
        witness_status=witness_status,
    )
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


def verify_chain(session: Session) -> str:
    provider = StubSealProvider()
    rows = list(session.scalars(select(LedgerEntryRow).order_by(LedgerEntryRow.posted_at)).all())
    prev: str | None = None
    for row in rows:
        seal_data = row.seal_payload
        manifest_sha = seal_data["manifest_sha256"]
        status = provider.witness(row.entry_hash, manifest_sha, prev)
        if status != "match":
            return "mismatch"
        prev = row.entry_hash
    return "match"
