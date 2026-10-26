"""Field normalisation for metric comparison (see docs/metrics.md)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

TWO = Decimal("0.01")

HEADER_FIELDS = (
    "invoice_number",
    "invoice_date",
    "vendor_gstin",
    "buyer_gstin",
    "place_of_supply_state_code",
    "taxable_total",
    "cgst_total",
    "sgst_total",
    "igst_total",
    "grand_total",
)

LINE_MATCH_FIELDS = ("description", "hsn_sac", "total")


def normalise_scalar(field: str, value: Any) -> Any | None:
    if value is None:
        return None
    if field in ("vendor_gstin", "buyer_gstin"):
        return str(value).strip().upper()
    if field == "invoice_date":
        if isinstance(value, date):
            return value.isoformat()
        return str(value).strip()
    if field in (
        "taxable_total",
        "cgst_total",
        "sgst_total",
        "igst_total",
        "grand_total",
        "total",
    ):
        if isinstance(value, Decimal):
            return value.quantize(TWO)
        try:
            return Decimal(str(value)).quantize(TWO)
        except (InvalidOperation, ValueError):
            return str(value)
    if field == "hsn_sac":
        if value is None or value == "":
            return None
        return str(value).strip()
    if field == "description":
        return " ".join(str(value).split())
    return value


def values_match(field: str, truth: Any, pred: Any) -> bool:
    return normalise_scalar(field, truth) == normalise_scalar(field, pred)


def line_match_key(line: dict[str, Any]) -> tuple[Any, ...]:
    return tuple(normalise_scalar(f, line.get(f)) for f in LINE_MATCH_FIELDS)
