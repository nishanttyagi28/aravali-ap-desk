from __future__ import annotations

from docai.contracts.extracted import ExtractedInvoice
from docai.contracts.validation import IssueCode, IssueSeverity, ValidationIssue
from docai.contracts.vendor import InvoiceHistory
from docai.validate.util import financial_year, normalise_invoice_number


def check_duplicate(
    inv: ExtractedInvoice,
    history: InvoiceHistory,
    *,
    is_duplicate_case: bool = True,
) -> list[ValidationIssue]:
    if not inv.vendor_gstin or not inv.invoice_number or inv.invoice_date is None:
        return []
    norm = normalise_invoice_number(inv.invoice_number)
    fy = financial_year(inv.invoice_date)
    key = (inv.vendor_gstin.upper(), norm, fy)
    for rec in history.records:
        if (
            rec.vendor_gstin.upper() == key[0]
            and rec.normalised_invoice_number == key[1]
            and rec.financial_year == key[2]
            and rec.invoice_id != inv.invoice_id
        ):
            return [
                ValidationIssue(
                    code=IssueCode.DUPLICATE_INVOICE,
                    severity=IssueSeverity.ERROR,
                    field="invoice_number",
                    message="Duplicate invoice for vendor in the same financial year",
                    evidence={"duplicate_of": str(rec.invoice_id)},
                )
            ]
    return []
