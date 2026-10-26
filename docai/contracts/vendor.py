"""Vendor master and invoice history."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict


class Vendor(BaseModel):
    model_config = ConfigDict(extra="forbid")

    vendor_id: str
    legal_name: str
    gstin: str
    state_code: str
    pan: str
    bank_last4: str | None = None


class VendorMaster(BaseModel):
    model_config = ConfigDict(extra="forbid")

    vendors: list[Vendor]

    def lookup_by_gstin(self, gstin: str) -> Vendor | None:
        key = gstin.upper()
        for v in self.vendors:
            if v.gstin.upper() == key:
                return v
        return None


class InvoiceHistoryRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    vendor_gstin: str
    normalised_invoice_number: str
    financial_year: str
    invoice_id: UUID


class InvoiceHistory(BaseModel):
    """Ordered duplicate-detection index (manifest build order)."""

    model_config = ConfigDict(extra="forbid")

    records: list[InvoiceHistoryRecord]
