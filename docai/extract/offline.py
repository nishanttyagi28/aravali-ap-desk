"""Rule-based offline invoice extraction."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from docai.contracts.bbox import BBox
from docai.contracts.extracted import (
    ExtractedField,
    ExtractedInvoice,
    ExtractionMode,
    FieldSource,
    LineItem,
)
from docai.extract.version import EXTRACTOR_VERSION
from docai.ingest.models import Document, Word

GSTIN_RE = re.compile(r"\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]")
INV_NO_RE = re.compile(r"INV-[\w-]+", re.IGNORECASE)
DATE_PATTERNS = [
    (re.compile(r"\b(\d{2})[-/](\d{2})[-/](\d{4})\b"), "dmy"),
    (re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b"), "iso"),
    (
        re.compile(
            r"\b(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{4})\b",
            re.IGNORECASE,
        ),
        "dmony",
    ),
]
AMOUNT_RE = re.compile(r"[\d,]+\.\d{2}")
STATE_CODE_RE = re.compile(r"\b(\d{2})\b")

CONF_ANCHOR = 0.92
CONF_REGEX = 0.78
CONF_INFERRED = 0.55
CONF_LOW = 0.25

LINE_Y_TOLERANCE = 4.0
# Classic synth layout omits a round-off row; infer from grand vs line totals when small.
MAX_INFERRED_ROUND_OFF = Decimal("2.00")


@dataclass
class TextLine:
    page: int
    y_mid: float
    words: list[Word]

    @property
    def text(self) -> str:
        return " ".join(w.text for w in self.words)

    def words_right_of(self, x: float) -> list[Word]:
        return [w for w in self.words if w.x0 >= x - 1]


def _words_bbox(words: list[Word], page: int) -> BBox | None:
    if not words:
        return None
    return BBox(
        page=page,
        x0=min(w.x0 for w in words),
        y0=min(w.y0 for w in words),
        x1=max(w.x1 for w in words),
        y1=max(w.y1 for w in words),
    )


def _cluster_lines(words: list[Word]) -> list[TextLine]:
    if not words:
        return []
    sorted_words = sorted(words, key=lambda w: (-w.y0, w.x0))
    lines: list[TextLine] = []
    for w in sorted_words:
        y_mid = (w.y0 + w.y1) / 2
        placed = False
        for line in lines:
            if line.page == w.page and abs(line.y_mid - y_mid) <= LINE_Y_TOLERANCE:
                line.words.append(w)
                line.y_mid = sum((x.y0 + x.y1) / 2 for x in line.words) / len(line.words)
                placed = True
                break
        if not placed:
            lines.append(TextLine(page=w.page, y_mid=y_mid, words=[w]))
    for line in lines:
        line.words.sort(key=lambda w: w.x0)
    lines.sort(key=lambda ln: (-ln.y_mid, ln.page))
    return lines


def _parse_amount(text: str) -> Decimal | None:
    m = AMOUNT_RE.search(text.replace(" ", ""))
    if not m:
        return None
    try:
        return Decimal(m.group(0).replace(",", ""))
    except InvalidOperation:
        return None


def _parse_date(text: str) -> date | None:
    for pattern, kind in DATE_PATTERNS:
        m = pattern.search(text)
        if not m:
            continue
        try:
            if kind == "dmy":
                d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
                return date(y, mo, d)
            if kind == "iso":
                y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
                return date(y, mo, d)
            if kind == "dmony":
                d = int(m.group(1))
                mo_str = m.group(2).title()[:3]
                y = int(m.group(3))
                mo = datetime.strptime(mo_str, "%b").month
                return date(y, mo, d)
        except ValueError:
            continue
    return None


def _find_label_line(lines: list[TextLine], *fragments: str) -> TextLine | None:
    frags = [f.lower() for f in fragments]
    for line in lines:
        t = line.text.lower()
        if all(f in t for f in frags):
            return line
    return None


def _norm_label(text: str) -> str:
    return text.lower().replace(" ", "")


def _find_footer_label_line(lines: list[TextLine], label: str) -> TextLine | None:
    """Match summary rows like ``CGST: 1,234.56`` (colon required), prefer lowest on page."""
    needle = _norm_label(f"{label}:")
    matches = [ln for ln in lines if needle in _norm_label(ln.text)]
    if not matches:
        return None
    return min(matches, key=lambda ln: ln.y_mid)


def _value_after_label(
    line: TextLine, label_end_x: float
) -> tuple[str | None, list[Word], BBox | None]:
    value_words = line.words_right_of(label_end_x)
    if not value_words:
        return None, [], None
    text = " ".join(w.text for w in value_words)
    return text.strip(), value_words, _words_bbox(value_words, line.page)


def _label_end_x(line: TextLine, label: str) -> float:
    """Approximate x after the label tokens on the line."""
    t = line.text
    idx = t.lower().find(label.lower())
    if idx < 0:
        return line.words[0].x0 if line.words else 0.0
    consumed = 0
    for w in line.words:
        consumed += len(w.text) + 1
        if consumed >= idx + len(label):
            return w.x1
    return line.words[-1].x1 if line.words else 0.0


def _make_field(
    name: str,
    value: Any,
    raw: str | None,
    bbox: BBox | None,
    confidence: float,
) -> ExtractedField:
    return ExtractedField(
        name=name,
        value=value,
        raw_text=raw,
        bbox=bbox,
        confidence=confidence,
        source=FieldSource.RULE,
    )


def _extract_scalar_fields(lines: list[TextLine], words: list[Word]) -> dict[str, ExtractedField]:
    fields: dict[str, ExtractedField] = {}

    def set_field(
        key: str,
        value: Any,
        raw: str,
        bbox: BBox | None,
        conf: float,
    ) -> None:
        fields[key] = _make_field(key, value, raw, bbox, conf)

    seller_line = _find_label_line(lines, "seller", "gstin")
    if seller_line:
        raw, vwords, bbox = _value_after_label(seller_line, _label_end_x(seller_line, "GSTIN:"))
        gst = GSTIN_RE.search(raw or "")
        if gst:
            set_field("vendor_gstin", gst.group(0), gst.group(0), bbox, CONF_ANCHOR)

    buyer_line = _find_label_line(lines, "buyer", "gstin")
    if buyer_line:
        raw, vwords, bbox = _value_after_label(buyer_line, _label_end_x(buyer_line, "GSTIN:"))
        gst = GSTIN_RE.search(raw or "")
        if gst:
            set_field("buyer_gstin", gst.group(0), gst.group(0), bbox, CONF_ANCHOR)

    pos_line = _find_label_line(lines, "place", "supply")
    if pos_line:
        raw, _, bbox = _value_after_label(pos_line, _label_end_x(pos_line, "Supply:"))
        code = STATE_CODE_RE.search(raw or "")
        if code:
            set_field("place_of_supply_state_code", code.group(1), code.group(1), bbox, CONF_ANCHOR)

    inv_line = _find_label_line(lines, "invoice", "no")
    if inv_line:
        raw, _, bbox = _value_after_label(inv_line, _label_end_x(inv_line, "No:"))
        if raw:
            inv = INV_NO_RE.search(raw) or re.search(r"\S+", raw)
            val = inv.group(0) if inv else raw.strip()
            set_field("invoice_number", val, val, bbox, CONF_ANCHOR)

    date_line = _find_label_line(lines, "invoice", "date")
    if date_line:
        raw, _, bbox = _value_after_label(date_line, _label_end_x(date_line, "Date:"))
        if raw and raw.strip():
            parsed = _parse_date(raw)
            if parsed:
                set_field("invoice_date", parsed, parsed.isoformat(), bbox, CONF_ANCHOR)
            else:
                set_field("invoice_date", None, raw, bbox, CONF_LOW)
        else:
            fields["invoice_date"] = _make_field("invoice_date", None, None, None, CONF_LOW)

    for key, label in (
        ("taxable_total", "Taxable"),
        ("cgst_total", "CGST"),
        ("sgst_total", "SGST"),
        ("igst_total", "IGST"),
        ("grand_total", "Grand Total"),
    ):
        line = _find_footer_label_line(lines, label)
        if not line:
            continue
        label_token = f"{label}:"
        raw, _, bbox = _value_after_label(line, _label_end_x(line, label_token))
        amt = _parse_amount(raw or "")
        if amt is not None:
            set_field(key, amt, raw or str(amt), bbox, CONF_ANCHOR)

    all_gstins = GSTIN_RE.findall(" ".join(w.text for w in words))
    if "vendor_gstin" not in fields and all_gstins:
        first = all_gstins[0]
        w = next((x for x in words if first in x.text), None)
        bbox = BBox(page=w.page, x0=w.x0, y0=w.y0, x1=w.x1, y1=w.y1) if w else None
        set_field("vendor_gstin", first, first, bbox, CONF_REGEX)
    if "buyer_gstin" not in fields and len(all_gstins) > 1:
        second = all_gstins[1]
        w = next((x for x in words if second in x.text), None)
        bbox = BBox(page=w.page, x0=w.x0, y0=w.y0, x1=w.x1, y1=w.y1) if w else None
        set_field("buyer_gstin", second, second, bbox, CONF_REGEX)

    if "invoice_number" not in fields:
        for line in lines:
            m = INV_NO_RE.search(line.text)
            if m:
                val = m.group(0)
                w = next((x for x in line.words if val in x.text or x.text in val), line.words[0])
                bbox = BBox(page=w.page, x0=w.x0, y0=w.y0, x1=w.x1, y1=w.y1)
                set_field("invoice_number", val, val, bbox, CONF_REGEX)
                break

    if "invoice_date" not in fields:
        for line in lines:
            parsed = _parse_date(line.text)
            if parsed:
                bbox = _words_bbox(line.words, line.page)
                set_field("invoice_date", parsed, parsed.isoformat(), bbox, CONF_REGEX)
                break

    return fields


@dataclass
class Column:
    name: str
    x0: float
    x1: float


def _column_ranges(header_line: TextLine) -> list[Column]:
    headers = [
        ("description", "description"),
        ("hsn", "hsn"),
        ("qty", "qty"),
        ("rate", "rate"),
        ("taxable", "taxable"),
        ("cgst", "cgst"),
        ("sgst", "sgst"),
        ("igst", "igst"),
        ("total", "total"),
    ]
    cols: list[Column] = []
    for key, token in headers:
        for w in header_line.words:
            if w.text.lower().startswith(token):
                cols.append(Column(key, w.x0 - 2, w.x1 + 40))
                break
    if len(cols) < 3:
        return []
    cols.sort(key=lambda c: c.x0)
    for i in range(len(cols) - 1):
        mid = (cols[i].x1 + cols[i + 1].x0) / 2
        cols[i].x1 = mid
        cols[i + 1].x0 = mid
    cols[-1].x1 = header_line.words[-1].x1 + 200
    cols[0].x0 = header_line.words[0].x0 - 2
    return cols


def _assign_column(word: Word, columns: list[Column]) -> str | None:
    cx = (word.x0 + word.x1) / 2
    for col in columns:
        if col.x0 <= cx <= col.x1:
            return col.name
    return None


def _parse_line_items(lines: list[TextLine]) -> list[LineItem]:
    header = _find_label_line(lines, "description")
    if not header or "hsn" not in header.text.lower():
        return []
    columns = _column_ranges(header)
    if not columns:
        return []

    header_y = header.y_mid
    totals_line = _find_footer_label_line(lines, "Taxable")
    stop_y = totals_line.y_mid if totals_line else 0.0

    interstate = _find_label_line(lines, "igst") is not None and "cgst" not in header.text.lower()

    row_lines = [
        ln for ln in lines if ln.y_mid < header_y - 2 and (stop_y == 0.0 or ln.y_mid > stop_y + 2)
    ]

    items: list[LineItem] = []
    for ln in row_lines:
        if "description" in ln.text.lower() and "hsn" in ln.text.lower():
            continue
        cells: dict[str, list[Word]] = {c.name: [] for c in columns}
        for w in ln.words:
            col = _assign_column(w, columns)
            if col:
                cells[col].append(w)

        desc = " ".join(w.text for w in cells.get("description", [])).strip()
        if not desc:
            continue
        hsn = " ".join(w.text for w in cells.get("hsn", [])).strip() or None
        qty_text = " ".join(w.text for w in cells.get("qty", []))
        rate_text = " ".join(w.text for w in cells.get("rate", []))
        taxable_text = " ".join(w.text for w in cells.get("taxable", []))
        cgst_text = " ".join(w.text for w in cells.get("cgst", []))
        sgst_text = " ".join(w.text for w in cells.get("sgst", []))
        igst_text = " ".join(w.text for w in cells.get("igst", []))
        total_text = " ".join(w.text for w in cells.get("total", []))

        qty = _parse_amount(qty_text) or Decimal("0")
        if qty == 0:
            try:
                qty = Decimal(re.sub(r"[^\d.]", "", qty_text) or "0")
            except InvalidOperation:
                qty = Decimal("0")

        unit_price = _parse_amount(rate_text) or Decimal("0")
        taxable_value = _parse_amount(taxable_text) or Decimal("0")
        cgst = _parse_amount(cgst_text) or Decimal("0")
        sgst = _parse_amount(sgst_text) or Decimal("0")
        igst = _parse_amount(igst_text) or Decimal("0")
        total = _parse_amount(total_text) or Decimal("0")

        if taxable_value == 0 and total == 0:
            continue

        if interstate:
            gst_rate = (
                (igst / taxable_value * Decimal("100")).quantize(Decimal("0.01"))
                if taxable_value
                else Decimal("0")
            )
        else:
            gst_rate = (
                ((cgst + sgst) / taxable_value * Decimal("100")).quantize(Decimal("0.01"))
                if taxable_value
                else Decimal("0")
            )

        items.append(
            LineItem(
                description=desc,
                hsn_sac=hsn,
                qty=qty,
                unit_price=unit_price,
                taxable_value=taxable_value,
                gst_rate=gst_rate,
                cgst=cgst,
                sgst=sgst,
                igst=igst,
                cess=Decimal("0"),
                total=total,
            )
        )
    return items


def extract_offline(document: Document, source_file: str) -> ExtractedInvoice:
    lines = _cluster_lines(document.words)
    fields = _extract_scalar_fields(lines, document.words)
    line_items = _parse_line_items(lines)

    def scalar(name: str, default: Any = None) -> Any:
        if name in fields:
            return fields[name].value
        return default

    taxable = scalar("taxable_total", Decimal("0")) or Decimal("0")
    cgst = scalar("cgst_total", Decimal("0")) or Decimal("0")
    sgst = scalar("sgst_total", Decimal("0")) or Decimal("0")
    igst = scalar("igst_total", Decimal("0")) or Decimal("0")
    grand = scalar("grand_total", Decimal("0")) or Decimal("0")

    if grand == 0 and line_items:
        grand = sum((li.total for li in line_items), Decimal("0"))

    sum_line_totals = sum((li.total for li in line_items), Decimal("0"))
    round_off = Decimal("0")
    if line_items and grand != 0:
        delta = grand - sum_line_totals
        if delta != 0 and abs(delta) <= MAX_INFERRED_ROUND_OFF:
            round_off = delta

    scalar_values: dict[str, Any] = {
        "invoice_number": scalar("invoice_number"),
        "invoice_date": scalar("invoice_date"),
        "vendor_gstin": scalar("vendor_gstin"),
        "buyer_gstin": scalar("buyer_gstin"),
        "place_of_supply_state_code": scalar("place_of_supply_state_code"),
        "taxable_total": taxable if isinstance(taxable, Decimal) else Decimal(str(taxable)),
        "cgst_total": cgst if isinstance(cgst, Decimal) else Decimal(str(cgst)),
        "sgst_total": sgst if isinstance(sgst, Decimal) else Decimal(str(sgst)),
        "igst_total": igst if isinstance(igst, Decimal) else Decimal(str(igst)),
        "grand_total": grand if isinstance(grand, Decimal) else Decimal(str(grand)),
    }
    for key, val in scalar_values.items():
        if key in fields:
            continue
        raw = val.isoformat() if isinstance(val, date) else (str(val) if val is not None else None)
        fields[key] = _make_field(key, val, raw, None, CONF_INFERRED)

    return ExtractedInvoice(
        invoice_id=uuid.uuid4(),
        source_file=source_file,
        sha256=document.sha256,
        page_count=document.page_count,
        invoice_number=scalar("invoice_number"),
        invoice_date=scalar("invoice_date"),
        vendor_gstin=scalar("vendor_gstin"),
        buyer_gstin=scalar("buyer_gstin"),
        place_of_supply_state_code=scalar("place_of_supply_state_code"),
        currency="INR",
        line_items=line_items,
        taxable_total=taxable if isinstance(taxable, Decimal) else Decimal(str(taxable)),
        cgst_total=cgst if isinstance(cgst, Decimal) else Decimal(str(cgst)),
        sgst_total=sgst if isinstance(sgst, Decimal) else Decimal(str(sgst)),
        igst_total=igst if isinstance(igst, Decimal) else Decimal(str(igst)),
        cess_total=Decimal("0"),
        round_off=round_off,
        grand_total=grand if isinstance(grand, Decimal) else Decimal(str(grand)),
        fields=fields,
        extractor_version=EXTRACTOR_VERSION,
        mode=ExtractionMode.OFFLINE,
    )
