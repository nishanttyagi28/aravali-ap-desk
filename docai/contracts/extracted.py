"""Extraction contracts."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from docai.contracts.bbox import BBox

ALLOWED_GST_RATES: frozenset[Decimal] = frozenset(
    {
        Decimal("0"),
        Decimal("0.25"),
        Decimal("3"),
        Decimal("5"),
        Decimal("12"),
        Decimal("18"),
        Decimal("28"),
    }
)


class FieldSource(StrEnum):
    TEXT_LAYER = "text_layer"
    OCR = "ocr"
    LLM = "llm"
    RULE = "rule"


class ExtractionMode(StrEnum):
    OFFLINE = "offline"
    LLM = "llm"


class ExtractedField(BaseModel):
    """One extracted scalar with provenance."""

    model_config = ConfigDict(extra="forbid")

    name: str
    value: Any
    raw_text: str | None = None
    bbox: BBox | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    source: FieldSource


class LineItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str
    hsn_sac: str | None = None
    qty: Decimal
    unit_price: Decimal
    taxable_value: Decimal
    gst_rate: Decimal
    cgst: Decimal
    sgst: Decimal
    igst: Decimal
    cess: Decimal = Decimal("0")
    total: Decimal


class ExtractedInvoice(BaseModel):
    model_config = ConfigDict(extra="forbid")

    invoice_id: UUID
    source_file: str
    sha256: str
    page_count: int = Field(ge=1)
    invoice_number: str | None = None
    invoice_date: date | None = None
    vendor_gstin: str | None = None
    buyer_gstin: str | None = None
    place_of_supply_state_code: str | None = None
    currency: str = "INR"
    line_items: list[LineItem]
    taxable_total: Decimal
    cgst_total: Decimal
    sgst_total: Decimal
    igst_total: Decimal
    cess_total: Decimal = Decimal("0")
    round_off: Decimal = Decimal("0")
    grand_total: Decimal
    fields: dict[str, ExtractedField]
    extractor_version: str
    mode: ExtractionMode
