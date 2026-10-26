"""SQLAlchemy 2.0 models."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class SchemaVersion(Base):
    __tablename__ = "schema_version"

    version: Mapped[int] = mapped_column(primary_key=True)
    applied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class VendorRow(Base):
    __tablename__ = "vendors"

    vendor_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    legal_name: Mapped[str] = mapped_column(String(256))
    gstin: Mapped[str] = mapped_column(String(15), unique=True, index=True)
    state_code: Mapped[str] = mapped_column(String(2))
    pan: Mapped[str] = mapped_column(String(10))
    bank_last4: Mapped[str | None] = mapped_column(String(4), nullable=True)


class InvoiceRow(Base):
    __tablename__ = "invoices"

    invoice_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    source_file: Mapped[str] = mapped_column(String(512))
    file_path: Mapped[str] = mapped_column(String(1024))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    vendor_gstin: Mapped[str | None] = mapped_column(String(15), nullable=True, index=True)
    invoice_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    posted: Mapped[bool] = mapped_column(Boolean, default=False)
    human_approved: Mapped[bool] = mapped_column(Boolean, default=False)

    decisions: Mapped[list[DecisionRow]] = relationship(back_populates="invoice")


class DecisionRow(Base):
    __tablename__ = "decisions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("invoices.invoice_id"), index=True
    )
    outcome: Mapped[str] = mapped_column(String(16))
    decided_by: Mapped[str] = mapped_column(String(16))
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)

    invoice: Mapped[InvoiceRow] = relationship(back_populates="decisions")


class ReviewActionRow(Base):
    __tablename__ = "review_actions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("invoices.invoice_id"), index=True
    )
    action: Mapped[str] = mapped_column(String(16))
    reviewer: Mapped[str] = mapped_column(String(128))
    corrections: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LedgerReceiptRow(Base):
    __tablename__ = "ledger_receipts"

    seq: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    entry_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("ledger_entries.entry_id"), unique=True, index=True
    )
    receipt_sha256: Mapped[str] = mapped_column(String(64))
    prev_receipt_sha256: Mapped[str] = mapped_column(String(64))
    body: Mapped[dict[str, Any]] = mapped_column(JSON)


class LedgerEntryRow(Base):
    __tablename__ = "ledger_entries"

    entry_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("invoices.invoice_id"), unique=True, index=True
    )
    vendor_id: Mapped[str] = mapped_column(String(32))
    taxable_total: Mapped[str] = mapped_column(String(32))
    cgst_total: Mapped[str] = mapped_column(String(32))
    sgst_total: Mapped[str] = mapped_column(String(32))
    igst_total: Mapped[str] = mapped_column(String(32))
    cess_total: Mapped[str] = mapped_column(String(32))
    grand_total: Mapped[str] = mapped_column(String(32))
    posted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    seal_payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    chain_prev_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    entry_hash: Mapped[str] = mapped_column(String(64))


class AuditLogRow(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(64))
    invoice_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    detail: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    message: Mapped[str] = mapped_column(Text)
