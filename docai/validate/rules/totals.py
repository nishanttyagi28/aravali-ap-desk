from __future__ import annotations

from decimal import Decimal

from docai.contracts.extracted import ExtractedInvoice
from docai.contracts.validation import IssueCode, IssueSeverity, ValidationIssue
from docai.validate.util import approx_equal


def check_totals(inv: ExtractedInvoice) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if not inv.line_items:
        return issues
    sum_taxable = sum((li.taxable_value for li in inv.line_items), Decimal("0"))
    sum_cgst = sum((li.cgst for li in inv.line_items), Decimal("0"))
    sum_sgst = sum((li.sgst for li in inv.line_items), Decimal("0"))
    sum_igst = sum((li.igst for li in inv.line_items), Decimal("0"))
    sum_cess = sum((li.cess for li in inv.line_items), Decimal("0"))
    sum_line_totals = sum((li.total for li in inv.line_items), Decimal("0"))

    if not approx_equal(sum_taxable, inv.taxable_total):
        issues.append(
            ValidationIssue(
                code=IssueCode.TOTAL_MISMATCH,
                severity=IssueSeverity.ERROR,
                field="taxable_total",
                message="Header taxable total does not match sum of lines",
            )
        )
    if not approx_equal(sum_cgst, inv.cgst_total):
        issues.append(
            ValidationIssue(
                code=IssueCode.TOTAL_MISMATCH,
                severity=IssueSeverity.ERROR,
                field="cgst_total",
                message="Header CGST total does not match sum of lines",
            )
        )
    if not approx_equal(sum_sgst, inv.sgst_total):
        issues.append(
            ValidationIssue(
                code=IssueCode.TOTAL_MISMATCH,
                severity=IssueSeverity.ERROR,
                field="sgst_total",
                message="Header SGST total does not match sum of lines",
            )
        )
    if not approx_equal(sum_igst, inv.igst_total):
        issues.append(
            ValidationIssue(
                code=IssueCode.TOTAL_MISMATCH,
                severity=IssueSeverity.ERROR,
                field="igst_total",
                message="Header IGST total does not match sum of lines",
            )
        )
    if not approx_equal(sum_cess, inv.cess_total):
        issues.append(
            ValidationIssue(
                code=IssueCode.TOTAL_MISMATCH,
                severity=IssueSeverity.ERROR,
                field="cess_total",
                message="Header cess total does not match sum of lines",
            )
        )
    expected_grand = sum_line_totals + inv.round_off
    if not approx_equal(expected_grand, inv.grand_total):
        issues.append(
            ValidationIssue(
                code=IssueCode.TOTAL_MISMATCH,
                severity=IssueSeverity.ERROR,
                field="grand_total",
                message="Grand total does not match line totals plus round-off",
                evidence={
                    "sum_line_totals": str(sum_line_totals),
                    "round_off": str(inv.round_off),
                    "grand_total": str(inv.grand_total),
                },
            )
        )
    return issues
