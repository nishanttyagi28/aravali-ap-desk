from __future__ import annotations

from docai.contracts.extracted import ALLOWED_GST_RATES, ExtractedInvoice
from docai.contracts.validation import IssueCode, IssueSeverity, ValidationIssue


def check_gst_rates(inv: ExtractedInvoice) -> list[ValidationIssue]:
    """Invalid statutory rates (handled in line arithmetic); kept for explicit ordering."""
    issues: list[ValidationIssue] = []
    for idx, line in enumerate(inv.line_items):
        if line.gst_rate not in ALLOWED_GST_RATES:
            issues.append(
                ValidationIssue(
                    code=IssueCode.LINE_ARITHMETIC,
                    severity=IssueSeverity.WARN,
                    field=f"line_items[{idx}].gst_rate",
                    message="GST rate is not an allowed statutory rate",
                    evidence={"gst_rate": str(line.gst_rate)},
                )
            )
    return issues
