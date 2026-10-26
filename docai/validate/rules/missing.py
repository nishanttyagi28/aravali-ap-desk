from __future__ import annotations

from docai.contracts.extracted import ExtractedInvoice
from docai.contracts.validation import IssueCode, IssueSeverity, ValidationIssue


def check_missing_fields(inv: ExtractedInvoice) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if not inv.invoice_number:
        issues.append(
            ValidationIssue(
                code=IssueCode.MISSING_FIELD,
                severity=IssueSeverity.WARN,
                field="invoice_number",
                message="Invoice number is required",
            )
        )
    if inv.invoice_date is None:
        issues.append(
            ValidationIssue(
                code=IssueCode.MISSING_FIELD,
                severity=IssueSeverity.WARN,
                field="invoice_date",
                message="Invoice date is required",
            )
        )
    if not inv.vendor_gstin:
        issues.append(
            ValidationIssue(
                code=IssueCode.MISSING_FIELD,
                severity=IssueSeverity.WARN,
                field="vendor_gstin",
                message="Vendor GSTIN is required",
            )
        )
    if not inv.line_items:
        issues.append(
            ValidationIssue(
                code=IssueCode.MISSING_FIELD,
                severity=IssueSeverity.WARN,
                field="line_items",
                message="At least one line item is required",
            )
        )
    else:
        for index, line in enumerate(inv.line_items):
            if not line.hsn_sac:
                issues.append(
                    ValidationIssue(
                        code=IssueCode.MISSING_FIELD,
                        severity=IssueSeverity.WARN,
                        field=f"line_items[{index}].hsn_sac",
                        message="HSN/SAC is required for each line item",
                    )
                )
    return issues
