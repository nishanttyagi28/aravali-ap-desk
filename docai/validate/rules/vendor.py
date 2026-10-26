from __future__ import annotations

import difflib

from docai.contracts.extracted import ExtractedInvoice
from docai.contracts.gstin import is_valid_gstin
from docai.contracts.validation import IssueCode, IssueSeverity, ValidationIssue
from docai.contracts.vendor import VendorMaster
from docai.validate.util import resolve_vendor_by_gstin

_NAME_MATCH_THRESHOLD = 0.75


def check_vendor(inv: ExtractedInvoice, vendors: VendorMaster) -> list[ValidationIssue]:
    gstin = inv.vendor_gstin
    if not gstin or not is_valid_gstin(gstin):
        return []
    vendor = resolve_vendor_by_gstin(gstin, vendors)
    if vendor is None:
        return [
            ValidationIssue(
                code=IssueCode.VENDOR_UNKNOWN,
                severity=IssueSeverity.ERROR,
                field="vendor_gstin",
                message="Vendor GSTIN is not in the vendor master",
                evidence={"gstin": gstin},
            )
        ]
    extracted_name = _extract_vendor_name(inv)
    if extracted_name:
        ratio = difflib.SequenceMatcher(
            None, extracted_name.lower(), vendor.legal_name.lower()
        ).ratio()
        if ratio < _NAME_MATCH_THRESHOLD:
            return [
                ValidationIssue(
                    code=IssueCode.LOW_CONFIDENCE,
                    severity=IssueSeverity.WARN,
                    field="vendor_gstin",
                    message="Vendor legal name does not closely match vendor master",
                    evidence={"ratio": ratio, "master_name": vendor.legal_name},
                )
            ]
    return []


def _extract_vendor_name(inv: ExtractedInvoice) -> str | None:
    field = inv.fields.get("vendor_name") or inv.fields.get("seller_name")
    if field and field.value:
        return str(field.value)
    return None
