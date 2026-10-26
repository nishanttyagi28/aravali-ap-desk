from __future__ import annotations

from decimal import Decimal

from docai.contracts.extracted import ALLOWED_GST_RATES, ExtractedInvoice
from docai.contracts.validation import IssueCode, IssueSeverity, ValidationIssue
from docai.validate.util import approx_equal


def check_line_arithmetic(inv: ExtractedInvoice) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for idx, line in enumerate(inv.line_items):
        expected_taxable = line.qty * line.unit_price
        if not approx_equal(expected_taxable, line.taxable_value):
            issues.append(
                ValidationIssue(
                    code=IssueCode.LINE_ARITHMETIC,
                    severity=IssueSeverity.ERROR,
                    field=f"line_items[{idx}].taxable_value",
                    message="Line taxable value does not equal qty × unit price",
                    evidence={
                        "qty": str(line.qty),
                        "unit_price": str(line.unit_price),
                        "taxable_value": str(line.taxable_value),
                    },
                )
            )
        rate = line.gst_rate
        if rate not in ALLOWED_GST_RATES:
            issues.append(
                ValidationIssue(
                    code=IssueCode.LINE_ARITHMETIC,
                    severity=IssueSeverity.WARN,
                    field=f"line_items[{idx}].gst_rate",
                    message="GST rate is not an allowed statutory rate",
                    evidence={"gst_rate": str(rate)},
                )
            )
            continue
        if rate > Decimal("0"):
            expected_tax = line.taxable_value * rate / Decimal("100")
            actual_tax = line.cgst + line.sgst + line.igst
            if not approx_equal(expected_tax, actual_tax):
                issues.append(
                    ValidationIssue(
                        code=IssueCode.LINE_ARITHMETIC,
                        severity=IssueSeverity.ERROR,
                        field=f"line_items[{idx}]",
                        message="Line tax does not equal taxable × GST rate",
                        evidence={
                            "expected_tax": str(expected_tax),
                            "actual_tax": str(actual_tax),
                        },
                    )
                )
        expected_total = line.taxable_value + line.cgst + line.sgst + line.igst + line.cess
        if not approx_equal(expected_total, line.total):
            issues.append(
                ValidationIssue(
                    code=IssueCode.LINE_ARITHMETIC,
                    severity=IssueSeverity.ERROR,
                    field=f"line_items[{idx}].total",
                    message="Line total does not match taxable + taxes",
                    evidence={
                        "expected_total": str(expected_total),
                        "total": str(line.total),
                    },
                )
            )
    return issues
