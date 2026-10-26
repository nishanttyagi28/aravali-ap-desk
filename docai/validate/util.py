"""Shared validation helpers."""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal

TOLERANCE = Decimal("0.01")
ROUND_OFF_LIMIT = Decimal("1.00")

_KEY_FIELDS = (
    "invoice_number",
    "invoice_date",
    "vendor_gstin",
    "buyer_gstin",
    "grand_total",
)


def normalise_invoice_number(number: str) -> str:
    return re.sub(r"\s+", "", number).upper()


def financial_year(invoice_date: date) -> str:
    """Indian FY label (April–March), e.g. 2025-04-01 -> ``2025-26``."""
    start = invoice_date.year if invoice_date.month >= 4 else invoice_date.year - 1
    return f"{start}-{str(start + 1)[-2:]}"


def approx_equal(a: Decimal, b: Decimal, tol: Decimal = TOLERANCE) -> bool:
    return abs(a - b) <= tol


def key_field_names() -> tuple[str, ...]:
    return _KEY_FIELDS


def resolve_vendor_by_gstin(gstin: str, vendors) -> object | None:
    from docai.contracts.vendor import VendorMaster

    master: VendorMaster = vendors
    vendor = master.lookup_by_gstin(gstin)
    if vendor is not None:
        return vendor
    if len(gstin) >= 12:
        pan = gstin[2:12].upper()
        for candidate in master.vendors:
            if candidate.pan.upper() == pan:
                return candidate
    return None
