"""KarmaSakshi-style effect receipt canonicalisation and hashing."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any
from uuid import UUID

GENESIS_PREV_RECEIPT_SHA256 = "0" * 64

_AMOUNT_KEYS = (
    "taxable_total",
    "cgst_total",
    "sgst_total",
    "igst_total",
    "cess_total",
    "grand_total",
)


def money_str(value: Decimal | str) -> str:
    d = value if isinstance(value, Decimal) else Decimal(str(value))
    return str(d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def amounts_dict(
    *,
    taxable_total: Decimal,
    cgst_total: Decimal,
    sgst_total: Decimal,
    igst_total: Decimal,
    cess_total: Decimal,
    grand_total: Decimal,
) -> dict[str, str]:
    return {
        "taxable_total": money_str(taxable_total),
        "cgst_total": money_str(cgst_total),
        "sgst_total": money_str(sgst_total),
        "igst_total": money_str(igst_total),
        "cess_total": money_str(cess_total),
        "grand_total": money_str(grand_total),
    }


def build_receipt_body(
    *,
    entry_id: UUID,
    invoice_id: UUID,
    vendor_id: str,
    taxable_total: Decimal,
    cgst_total: Decimal,
    sgst_total: Decimal,
    igst_total: Decimal,
    cess_total: Decimal,
    grand_total: Decimal,
    posted_at: datetime,
    prev_receipt_sha256: str,
    seq: int,
) -> dict[str, Any]:
    posted = posted_at.isoformat()
    return {
        "amounts": amounts_dict(
            taxable_total=taxable_total,
            cgst_total=cgst_total,
            sgst_total=sgst_total,
            igst_total=igst_total,
            cess_total=cess_total,
            grand_total=grand_total,
        ),
        "entry_id": str(entry_id),
        "invoice_id": str(invoice_id),
        "posted_at": posted,
        "prev_receipt_sha256": prev_receipt_sha256,
        "seq": seq,
        "vendor_id": vendor_id,
    }


def canonical_receipt_json(body: dict[str, Any]) -> str:
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def receipt_sha256(body: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_receipt_json(body).encode("utf-8")).hexdigest()
