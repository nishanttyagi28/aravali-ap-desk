from __future__ import annotations

from decimal import Decimal

from docai.contracts.extracted import ExtractedInvoice
from docai.contracts.validation import IssueCode, IssueSeverity, ValidationIssue
from docai.validate.util import approx_equal


def _regime_from_pos(inv: ExtractedInvoice) -> bool | None:
    pos = inv.place_of_supply_state_code
    vendor_state = (inv.vendor_gstin or "")[:2].upper() if inv.vendor_gstin else None
    if not pos or not vendor_state or len(vendor_state) != 2:
        return None
    return pos.upper() != vendor_state


def _regime_from_lines(inv: ExtractedInvoice) -> bool | None:
    if not inv.line_items:
        return None
    has_igst = any(line.igst > Decimal("0") for line in inv.line_items)
    has_cgst_sgst = any(
        line.cgst > Decimal("0") or line.sgst > Decimal("0") for line in inv.line_items
    )
    if has_igst and not has_cgst_sgst:
        return True
    if has_cgst_sgst and not has_igst:
        return False
    return None


def check_tax_regime(inv: ExtractedInvoice) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    line_inter = _regime_from_lines(inv)
    pos = inv.place_of_supply_state_code
    vendor_state = (inv.vendor_gstin or "")[:2].upper() if inv.vendor_gstin else None
    buyer_state = (inv.buyer_gstin or "")[:2].upper() if inv.buyer_gstin else None
    if (
        line_inter
        and pos
        and vendor_state
        and pos.upper() == vendor_state
        and buyer_state
        and buyer_state != pos.upper()
    ):
        issues.append(
            ValidationIssue(
                code=IssueCode.TAX_REGIME_MISMATCH,
                severity=IssueSeverity.ERROR,
                field="place_of_supply_state_code",
                message="Place of supply regime disagrees with line tax split",
            )
        )
    interstate = line_inter if line_inter is not None else _regime_from_pos(inv)
    if interstate is None:
        return issues
    for idx, line in enumerate(inv.line_items):
        if interstate:
            if not approx_equal(line.cgst, Decimal("0")) or not approx_equal(
                line.sgst, Decimal("0")
            ):
                issues.append(
                    ValidationIssue(
                        code=IssueCode.TAX_REGIME_MISMATCH,
                        severity=IssueSeverity.ERROR,
                        field=f"line_items[{idx}]",
                        message="Inter-state supply must not have CGST/SGST on line",
                        evidence={"line_index": idx},
                    )
                )
            if line.igst <= Decimal("0") and line.gst_rate > Decimal("0"):
                issues.append(
                    ValidationIssue(
                        code=IssueCode.TAX_REGIME_MISMATCH,
                        severity=IssueSeverity.ERROR,
                        field=f"line_items[{idx}]",
                        message="Inter-state supply requires IGST on taxable lines",
                        evidence={"line_index": idx},
                    )
                )
        else:
            if not approx_equal(line.igst, Decimal("0")):
                issues.append(
                    ValidationIssue(
                        code=IssueCode.TAX_REGIME_MISMATCH,
                        severity=IssueSeverity.ERROR,
                        field=f"line_items[{idx}]",
                        message="Intra-state supply must not have IGST on line",
                        evidence={"line_index": idx},
                    )
                )
            if line.gst_rate > Decimal("0") and (
                not approx_equal(line.cgst, line.sgst) or line.cgst <= Decimal("0")
            ):
                issues.append(
                    ValidationIssue(
                        code=IssueCode.TAX_REGIME_MISMATCH,
                        severity=IssueSeverity.ERROR,
                        field=f"line_items[{idx}]",
                        message="Intra-state supply requires equal CGST and SGST",
                        evidence={"line_index": idx},
                    )
                )
    return issues
