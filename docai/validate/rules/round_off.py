from __future__ import annotations

from docai.contracts.extracted import ExtractedInvoice
from docai.contracts.validation import IssueCode, IssueSeverity, ValidationIssue
from docai.validate.util import ROUND_OFF_LIMIT


def check_round_off(inv: ExtractedInvoice) -> list[ValidationIssue]:
    if abs(inv.round_off) > ROUND_OFF_LIMIT:
        return [
            ValidationIssue(
                code=IssueCode.ROUND_OFF_EXCEEDED,
                severity=IssueSeverity.WARN,
                field="round_off",
                message="Round-off magnitude exceeds ₹1.00",
                evidence={"round_off": str(inv.round_off)},
            )
        ]
    return []
