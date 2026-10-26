"""Deterministic Indian GST tax-invoice PDF + TruthRecord generator."""

from __future__ import annotations

import hashlib
import json
import random
import re
import uuid
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from docai.contracts.bbox import BBox
from docai.contracts.decision import DecisionOutcome
from docai.contracts.extracted import (
    ExtractedField,
    ExtractedInvoice,
    ExtractionMode,
    FieldSource,
    LineItem,
)
from docai.contracts.gstin import gstin_checksum_char
from docai.contracts.truth import TruthRecord
from docai.contracts.validation import IssueCode
from docai.contracts.vendor import Vendor, VendorMaster

GENERATOR_VERSION = "synth-v0"
TWO = Decimal("0.01")

BROKEN_CASES = [
    "bad_gstin_checksum",
    "gstin_state_mismatch",
    "tax_regime_mismatch",
    "line_arithmetic",
    "grand_total_mismatch",
    "duplicate_invoice",
    "unknown_vendor",
    "missing_invoice_date",
]
CLEAN_CASES = ["clean_intrastate", "clean_interstate"]


@dataclass
class LayoutBox:
    page: int
    x0: float
    y0: float
    x1: float
    y1: float

    def to_bbox(self) -> BBox:
        return BBox(page=self.page, x0=self.x0, y0=self.y0, x1=self.x1, y1=self.y1)


def _q(amount: Decimal) -> Decimal:
    return amount.quantize(TWO, rounding=ROUND_HALF_UP)


def _money_str(amount: Decimal) -> str:
    return f"{_q(amount):,.2f}"


def _make_pan(rng: random.Random) -> str:
    letters = "ABCDEFGHJKLMNPQRSTUVWXYZ"
    return (
        "".join(rng.choice(letters) for _ in range(5))
        + f"{rng.randint(1000, 9999)}{rng.choice(letters)}"
    )


def _make_gstin(
    state_code: str, pan: str, rng: random.Random, *, bad_checksum: bool = False
) -> str:
    body = f"{state_code}{pan}1Z"
    check = gstin_checksum_char(body)
    if bad_checksum:
        check = "0" if check != "0" else "1"
    return body + check


def _field(
    name: str, value: Any, raw: str, bbox: BBox | None, conf: float = 0.99
) -> ExtractedField:
    return ExtractedField(
        name=name,
        value=value,
        raw_text=raw,
        bbox=bbox,
        confidence=conf,
        source=FieldSource.TEXT_LAYER,
    )


def _assign_cases(n: int, seed: int) -> list[str]:
    rng = random.Random(seed)
    clean_target = int(round(0.7 * n))
    broken_count = n - clean_target
    cases: list[str] = []
    if n >= len(BROKEN_CASES):
        cases.extend(BROKEN_CASES)
        for _ in range(broken_count - len(BROKEN_CASES)):
            cases.append(rng.choice(BROKEN_CASES))
    else:
        cases.extend(rng.sample(BROKEN_CASES, k=broken_count))
    for _ in range(clean_target):
        cases.append(rng.choice(CLEAN_CASES))
    rng.shuffle(cases)
    if "duplicate_invoice" in cases and cases[0] == "duplicate_invoice" and len(cases) > 1:
        cases[0], cases[1] = cases[1], cases[0]
    return cases[:n]


def _vendor_pool(rng: random.Random) -> list[Vendor]:
    pool: list[Vendor] = []
    states = ["07", "09", "27", "29", "33"]
    for i, st in enumerate(states):
        pan = _make_pan(rng)
        gstin = _make_gstin(st, pan, rng)
        pool.append(
            Vendor(
                vendor_id=f"V{i + 1:03d}",
                legal_name=f"Aravali Supplies {i + 1} Pvt Ltd",
                gstin=gstin,
                state_code=st,
                pan=pan,
                bank_last4=f"{1000 + i}",
            )
        )
    return pool


def _buyer_gstin(rng: random.Random) -> tuple[str, str]:
    st = rng.choice(["07", "27"])
    pan = _make_pan(rng)
    return _make_gstin(st, pan, rng), st


def _line_items(
    rng: random.Random, interstate: bool, *, break_arithmetic: bool = False
) -> tuple[list[LineItem], list[dict[str, Any]]]:
    rates = [Decimal("5"), Decimal("12"), Decimal("18")]
    items: list[LineItem] = []
    rows: list[dict[str, Any]] = []
    for idx in range(rng.randint(1, 3)):
        rate = rng.choice(rates)
        qty = Decimal(str(rng.randint(1, 10)))
        unit = Decimal(str(rng.choice([100, 250, 499.5])))
        taxable = _q(qty * unit)
        if interstate:
            igst = _q(taxable * rate / Decimal("100"))
            cgst = sgst = Decimal("0")
        else:
            half = _q(taxable * rate / Decimal("200"))
            cgst = sgst = half
            igst = Decimal("0")
        total = _q(taxable + cgst + sgst + igst)
        if break_arithmetic and idx == 0:
            total += Decimal("1.00")
        desc = f"Item {idx + 1} — Industrial goods"
        hsn = f"{rng.randint(1000, 9999)}"
        items.append(
            LineItem(
                description=desc,
                hsn_sac=hsn,
                qty=qty,
                unit_price=unit,
                taxable_value=taxable,
                gst_rate=rate,
                cgst=cgst,
                sgst=sgst,
                igst=igst,
                cess=Decimal("0"),
                total=total,
            )
        )
        rows.append(
            {
                "description": desc,
                "hsn": hsn,
                "qty": str(qty),
                "rate": _money_str(unit),
                "taxable": _money_str(taxable),
                "cgst": _money_str(cgst),
                "sgst": _money_str(sgst),
                "igst": _money_str(igst),
                "total": _money_str(total),
            }
        )
    return items, rows


def _totals(items: list[LineItem]) -> dict[str, Decimal]:
    taxable = _q(sum((i.taxable_value for i in items), Decimal("0")))
    cgst = _q(sum((i.cgst for i in items), Decimal("0")))
    sgst = _q(sum((i.sgst for i in items), Decimal("0")))
    igst = _q(sum((i.igst for i in items), Decimal("0")))
    grand = _q(taxable + cgst + sgst + igst)
    return {
        "taxable_total": taxable,
        "cgst_total": cgst,
        "sgst_total": sgst,
        "igst_total": igst,
        "cess_total": Decimal("0"),
        "round_off": Decimal("0"),
        "grand_total": grand,
    }


def _draw_invoice_pdf(
    path: Path,
    *,
    seller: Vendor,
    buyer_gstin: str,
    buyer_state: str,
    invoice_number: str,
    invoice_date: date | None,
    place_of_supply: str,
    rows: list[dict[str, Any]],
    totals: dict[str, Decimal],
    interstate: bool,
) -> dict[str, LayoutBox]:
    width, height = A4
    c = canvas.Canvas(str(path), pagesize=A4, invariant=1)
    boxes: dict[str, LayoutBox] = {}
    page = 1
    y = height - 25 * mm

    def draw_label_value(key: str, label: str, value: str, x: float, y_pos: float) -> float:
        c.setFont("Helvetica-Bold", 9)
        c.drawString(x, y_pos, label)
        c.setFont("Helvetica", 10)
        c.drawString(x + 35 * mm, y_pos, value)
        w = c.stringWidth(value, "Helvetica", 10)
        boxes[key] = LayoutBox(page, x + 35 * mm, y_pos - 2, x + 35 * mm + w, y_pos + 10)
        return y_pos - 6 * mm

    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(width / 2, y, "TAX INVOICE")
    y -= 10 * mm

    y = draw_label_value("vendor_gstin", "Seller GSTIN:", seller.gstin, 20 * mm, y)
    c.setFont("Helvetica", 10)
    c.drawString(20 * mm, y, seller.legal_name)
    y -= 8 * mm
    y = draw_label_value("buyer_gstin", "Buyer GSTIN:", buyer_gstin, 20 * mm, y)
    y = draw_label_value(
        "place_of_supply_state_code", "Place of Supply:", place_of_supply, 20 * mm, y
    )
    y = draw_label_value("invoice_number", "Invoice No:", invoice_number, 20 * mm, y)
    date_str = invoice_date.isoformat() if invoice_date else ""
    if invoice_date:
        y = draw_label_value("invoice_date", "Invoice Date:", date_str, 20 * mm, y)
    else:
        c.setFont("Helvetica-Bold", 9)
        c.drawString(20 * mm, y, "Invoice Date:")
        y -= 6 * mm

    y -= 4 * mm
    c.setFont("Helvetica-Bold", 9)
    headers = ["Description", "HSN", "Qty", "Rate", "Taxable"]
    if interstate:
        headers += ["IGST", "Total"]
    else:
        headers += ["CGST", "SGST", "Total"]
    xs = [20 * mm, 70 * mm, 105 * mm, 120 * mm, 140 * mm]
    if interstate:
        xs += [165 * mm, 185 * mm]
    else:
        xs += [160 * mm, 175 * mm, 190 * mm]
    for i, h in enumerate(headers):
        c.drawString(xs[i], y, h)
    y -= 5 * mm
    c.setFont("Helvetica", 9)
    for row in rows:
        c.drawString(xs[0], y, row["description"][:28])
        c.drawString(xs[1], y, row["hsn"])
        c.drawString(xs[2], y, row["qty"])
        c.drawString(xs[3], y, row["rate"])
        c.drawString(xs[4], y, row["taxable"])
        if interstate:
            c.drawString(xs[5], y, row["igst"])
            c.drawString(xs[6], y, row["total"])
        else:
            c.drawString(xs[5], y, row["cgst"])
            c.drawString(xs[6], y, row["sgst"])
            c.drawString(xs[7], y, row["total"])
        y -= 5 * mm

    y -= 4 * mm
    y = draw_label_value(
        "taxable_total", "Taxable:", _money_str(totals["taxable_total"]), 120 * mm, y
    )
    if interstate:
        y = draw_label_value("igst_total", "IGST:", _money_str(totals["igst_total"]), 120 * mm, y)
    else:
        y = draw_label_value("cgst_total", "CGST:", _money_str(totals["cgst_total"]), 120 * mm, y)
        y = draw_label_value("sgst_total", "SGST:", _money_str(totals["sgst_total"]), 120 * mm, y)
    y = draw_label_value(
        "grand_total", "Grand Total:", _money_str(totals["grand_total"]), 120 * mm, y
    )

    c.setStrokeColor(colors.grey)
    c.rect(15 * mm, 20 * mm, width - 30 * mm, height - 40 * mm)
    c.showPage()
    c.save()
    return boxes


def _expected_for_case(case: str) -> tuple[DecisionOutcome, list[IssueCode]]:
    mapping: dict[str, tuple[DecisionOutcome, list[IssueCode]]] = {
        "clean_intrastate": (DecisionOutcome.ALLOW, []),
        "clean_interstate": (DecisionOutcome.ALLOW, []),
        "bad_gstin_checksum": (DecisionOutcome.BLOCK, [IssueCode.GSTIN_CHECKSUM]),
        "gstin_state_mismatch": (DecisionOutcome.BLOCK, [IssueCode.GSTIN_STATE_MISMATCH]),
        "tax_regime_mismatch": (DecisionOutcome.BLOCK, [IssueCode.TAX_REGIME_MISMATCH]),
        "line_arithmetic": (DecisionOutcome.BLOCK, [IssueCode.LINE_ARITHMETIC]),
        "grand_total_mismatch": (DecisionOutcome.BLOCK, [IssueCode.TOTAL_MISMATCH]),
        "duplicate_invoice": (DecisionOutcome.BLOCK, [IssueCode.DUPLICATE_INVOICE]),
        "unknown_vendor": (DecisionOutcome.BLOCK, [IssueCode.VENDOR_UNKNOWN]),
        "missing_invoice_date": (DecisionOutcome.REVIEW, [IssueCode.MISSING_FIELD]),
    }
    return mapping[case]


def _build_truth(
    *,
    invoice_id: uuid.UUID,
    case: str,
    seller: Vendor,
    buyer_gstin: str,
    buyer_state: str,
    invoice_number: str,
    invoice_date: date | None,
    place_of_supply: str,
    items: list[LineItem],
    totals: dict[str, Decimal],
    layout: dict[str, LayoutBox],
    source_file: str,
    pdf_bytes: bytes,
    duplicate_of: uuid.UUID | None,
) -> TruthRecord:
    bboxes = {k: v.to_bbox() for k, v in layout.items()}
    fields: dict[str, ExtractedField] = {}
    for key in (
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
    ):
        val: Any
        if key == "invoice_number":
            val = invoice_number
        elif key == "invoice_date":
            val = invoice_date
        elif key == "vendor_gstin":
            val = seller.gstin
        elif key == "buyer_gstin":
            val = buyer_gstin
        elif key == "place_of_supply_state_code":
            val = place_of_supply
        else:
            val = totals[key]
        raw = invoice_date.isoformat() if key == "invoice_date" and invoice_date else str(val)
        fields[key] = _field(key, val, raw, bboxes.get(key))

    invoice = ExtractedInvoice(
        invoice_id=invoice_id,
        source_file=source_file,
        sha256=hashlib.sha256(pdf_bytes).hexdigest(),
        page_count=1,
        invoice_number=invoice_number,
        invoice_date=invoice_date,
        vendor_gstin=seller.gstin,
        buyer_gstin=buyer_gstin,
        place_of_supply_state_code=place_of_supply,
        currency="INR",
        line_items=items,
        taxable_total=totals["taxable_total"],
        cgst_total=totals["cgst_total"],
        sgst_total=totals["sgst_total"],
        igst_total=totals["igst_total"],
        cess_total=totals["cess_total"],
        round_off=totals["round_off"],
        grand_total=totals["grand_total"],
        fields=fields,
        extractor_version=GENERATOR_VERSION,
        mode=ExtractionMode.OFFLINE,
    )
    outcome, codes = _expected_for_case(case)
    return TruthRecord(
        invoice=invoice,
        expected_decision=outcome,
        expected_issue_codes=codes,
        bboxes=bboxes,
        duplicate_of=duplicate_of,
    )


def generate_dataset(
    n: int,
    seed: int,
    out_dir: Path,
    *,
    cases_override: list[str] | None = None,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    vendors = _vendor_pool(rng)
    master_vendors = list(vendors)
    cases = cases_override if cases_override is not None else _assign_cases(n, seed)
    if len(cases) != n:
        raise ValueError("cases_override length must equal n")
    case_counts: dict[str, int] = {}
    manifest_invoices: list[dict[str, Any]] = []
    seen_invoices: dict[tuple[str, str], uuid.UUID] = {}

    for i, case in enumerate(cases):
        case_counts[case] = case_counts.get(case, 0) + 1
        invoice_id = uuid.UUID(int=rng.getrandbits(128))
        inv_no = f"INV-{seed}-{i + 1:04d}"
        inv_date = date(2025, 4, 1) + timedelta(days=i % 120)
        seller = rng.choice(vendors)
        buyer_gstin, buyer_state = _buyer_gstin(rng)
        interstate = case == "clean_interstate" or case == "tax_regime_mismatch"
        if case == "tax_regime_mismatch":
            interstate = True
            buyer_state = seller.state_code
        if case == "clean_intrastate":
            interstate = False
            buyer_state = seller.state_code

        duplicate_of: uuid.UUID | None = None
        if case == "duplicate_invoice":
            if seen_invoices:
                key = next(iter(seen_invoices))
                prior = seen_invoices[key]
                duplicate_of = prior
                inv_no = key[1]
                seller = next(v for v in vendors if v.gstin == key[0])
            elif manifest_invoices:
                prior_id = uuid.UUID(manifest_invoices[-1]["id"])
                duplicate_of = prior_id
                inv_no = manifest_invoices[-1].get("_inv_no", inv_no)
        if case != "duplicate_invoice":
            seen_invoices[(seller.gstin, inv_no)] = invoice_id

        if case == "bad_gstin_checksum":
            seller = Vendor(
                vendor_id=seller.vendor_id,
                legal_name=seller.legal_name,
                gstin=_make_gstin(seller.state_code, seller.pan, rng, bad_checksum=True),
                state_code=seller.state_code,
                pan=seller.pan,
                bank_last4=seller.bank_last4,
            )
        if case == "gstin_state_mismatch":
            wrong_state = "01" if seller.state_code != "01" else "02"
            seller = Vendor(
                vendor_id=seller.vendor_id,
                legal_name=seller.legal_name,
                gstin=_make_gstin(wrong_state, seller.pan, rng),
                state_code=seller.state_code,
                pan=seller.pan,
                bank_last4=seller.bank_last4,
            )
        if case == "unknown_vendor":
            pan = _make_pan(rng)
            ghost = _make_gstin("32", pan, rng)
            seller = Vendor(
                vendor_id="V999",
                legal_name="Unregistered Ghost Traders",
                gstin=ghost,
                state_code="32",
                pan=pan,
            )
        break_arith = case == "line_arithmetic"
        items, rows = _line_items(rng, interstate, break_arithmetic=break_arith)
        totals = _totals(items)
        if case == "grand_total_mismatch":
            totals["grand_total"] = totals["grand_total"] + Decimal("10.00")
        if case == "missing_invoice_date":
            inv_date = None

        pdf_name = f"{invoice_id}.pdf"
        pdf_path = out_dir / pdf_name
        layout = _draw_invoice_pdf(
            pdf_path,
            seller=seller,
            buyer_gstin=buyer_gstin,
            buyer_state=buyer_state,
            invoice_number=inv_no,
            invoice_date=inv_date,
            place_of_supply=buyer_state,
            rows=rows,
            totals=totals,
            interstate=interstate,
        )
        pdf_bytes = pdf_path.read_bytes()
        truth = _build_truth(
            invoice_id=invoice_id,
            case=case,
            seller=seller,
            buyer_gstin=buyer_gstin,
            buyer_state=buyer_state,
            invoice_number=inv_no,
            invoice_date=inv_date,
            place_of_supply=buyer_state,
            items=items,
            totals=totals,
            layout=layout,
            source_file=pdf_name,
            pdf_bytes=pdf_bytes,
            duplicate_of=duplicate_of,
        )
        truth_path = out_dir / f"{invoice_id}.truth.json"
        truth_path.write_text(
            json.dumps(truth.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        manifest_invoices.append(
            {
                "id": str(invoice_id),
                "case": case,
                "duplicate_of": str(duplicate_of) if duplicate_of else None,
                "_inv_no": inv_no,
            }
        )

    master = VendorMaster(vendors=master_vendors)
    (out_dir / "vendor_master.json").write_text(
        json.dumps(master.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    public_invoices = [
        {k: v for k, v in row.items() if not k.startswith("_")} for row in manifest_invoices
    ]
    manifest = {
        "generator_version": GENERATOR_VERSION,
        "seed": seed,
        "count": n,
        "case_counts": case_counts,
        "invoices": public_invoices,
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return manifest


def normalise_invoice_number(number: str) -> str:
    return re.sub(r"\s+", "", number).upper()
