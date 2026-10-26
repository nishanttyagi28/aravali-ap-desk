"""Decision policy: map validation issue codes to ALLOW / REVIEW / BLOCK."""

from __future__ import annotations

from docai.contracts.decision import DecisionOutcome
from docai.contracts.validation import IssueCode, ValidationIssue

# Hard stops (including cases required by the M2 synthetic truth dataset).
BLOCK_CODES: frozenset[IssueCode] = frozenset(
    {
        IssueCode.GSTIN_CHECKSUM,
        IssueCode.GSTIN_STATE_MISMATCH,
        IssueCode.TAX_REGIME_MISMATCH,
        IssueCode.DUPLICATE_INVOICE,
        IssueCode.LINE_ARITHMETIC,
        IssueCode.TOTAL_MISMATCH,
        IssueCode.VENDOR_UNKNOWN,
    }
)

REVIEW_CODES: frozenset[IssueCode] = frozenset(
    {
        IssueCode.ROUND_OFF_EXCEEDED,
        IssueCode.LOW_CONFIDENCE,
        IssueCode.MISSING_FIELD,
    }
)


def outcome_from_issues(issues: list[ValidationIssue]) -> DecisionOutcome:
    if not issues:
        return DecisionOutcome.ALLOW
    codes = {issue.code for issue in issues}
    if codes & BLOCK_CODES:
        return DecisionOutcome.BLOCK
    if codes & REVIEW_CODES:
        return DecisionOutcome.REVIEW
    return DecisionOutcome.REVIEW
