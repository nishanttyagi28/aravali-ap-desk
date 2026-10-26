"""Ledger posting contracts."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SealProvider(StrEnum):
    STUB = "stub"
    KARMASAKSHI = "karmasakshi"


class WitnessStatus(StrEnum):
    PENDING = "pending"
    WITNESSED = "witnessed"
    FAILED = "failed"


class SealRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: SealProvider
    commit_id: str
    manifest_sha256: str
    witness_status: WitnessStatus


class LedgerEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entry_id: UUID
    invoice_id: UUID
    vendor_id: str
    taxable_total: Decimal
    cgst_total: Decimal
    sgst_total: Decimal
    igst_total: Decimal
    cess_total: Decimal
    grand_total: Decimal
    posted_at: datetime
    seal: SealRef
