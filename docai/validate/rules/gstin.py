from __future__ import annotations

from docai.contracts.extracted import ExtractedInvoice
from docai.contracts.gstin import is_valid_gstin
from docai.contracts.validation import IssueCode, IssueSeverity, ValidationIssue
from docai.contracts.vendor import VendorMaster
from docai.validate.util import resolve_vendor_by_gstin


def check_gstin_checksum(inv: ExtractedInvoice) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for field_name, gstin in (("vendor_gstin", inv.vendor_gstin), ("buyer_gstin", inv.buyer_gstin)):
        if not gstin:
            continue
        if not is_valid_gstin(gstin):
            issues.append(
                ValidationIssue(
                    code=IssueCode.GSTIN_CHECKSUM,
                    severity=IssueSeverity.ERROR,
                    field=field_name,
                    message=f"Invalid GSTIN checksum for {field_name}",
                    evidence={"gstin": gstin},
                )
            )
    return issues


def check_gstin_state(inv: ExtractedInvoice, vendors: VendorMaster) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    gstin = inv.vendor_gstin
    if not gstin or not is_valid_gstin(gstin):
        return issues
    vendor = resolve_vendor_by_gstin(gstin, vendors)
    if vendor is None:
        return issues
    if gstin[:2].upper() != vendor.state_code:
        issues.append(
            ValidationIssue(
                code=IssueCode.GSTIN_STATE_MISMATCH,
                severity=IssueSeverity.ERROR,
                field="vendor_gstin",
                message="Vendor GSTIN state code does not match vendor master state",
                evidence={
                    "gstin_state": gstin[:2],
                    "master_state": vendor.state_code,
                },
            )
        )
    return issues
