"""Table-driven tests for issue-code → decision outcome mapping."""

from __future__ import annotations

import pytest

from docai.contracts.decision import DecisionOutcome
from docai.contracts.validation import IssueCode, IssueSeverity, ValidationIssue
from docai.validate.policy import outcome_from_issues

# Product policy: synthetic truth labels are authoritative for test data.
ISSUE_TO_OUTCOME: list[tuple[IssueCode, DecisionOutcome]] = [
    (IssueCode.GSTIN_CHECKSUM, DecisionOutcome.BLOCK),
    (IssueCode.GSTIN_STATE_MISMATCH, DecisionOutcome.BLOCK),
    (IssueCode.TAX_REGIME_MISMATCH, DecisionOutcome.BLOCK),
    (IssueCode.DUPLICATE_INVOICE, DecisionOutcome.BLOCK),
    (IssueCode.LINE_ARITHMETIC, DecisionOutcome.BLOCK),
    (IssueCode.TOTAL_MISMATCH, DecisionOutcome.BLOCK),
    (IssueCode.VENDOR_UNKNOWN, DecisionOutcome.REVIEW),
    (IssueCode.ROUND_OFF_EXCEEDED, DecisionOutcome.REVIEW),
    (IssueCode.LOW_CONFIDENCE, DecisionOutcome.REVIEW),
    (IssueCode.MISSING_FIELD, DecisionOutcome.REVIEW),
]


@pytest.mark.parametrize(("code", "expected"), ISSUE_TO_OUTCOME)
def test_single_issue_maps_to_expected_outcome(code: IssueCode, expected: DecisionOutcome) -> None:
    issues = [
        ValidationIssue(
            code=code,
            severity=IssueSeverity.ERROR,
            message=f"test {code.value}",
            field=None,
            evidence=None,
        )
    ]
    assert outcome_from_issues(issues) == expected


def test_empty_issues_allow() -> None:
    assert outcome_from_issues([]) == DecisionOutcome.ALLOW


def test_block_wins_over_review() -> None:
    issues = [
        ValidationIssue(
            code=IssueCode.VENDOR_UNKNOWN,
            severity=IssueSeverity.WARN,
            message="unknown",
            field=None,
            evidence=None,
        ),
        ValidationIssue(
            code=IssueCode.LINE_ARITHMETIC,
            severity=IssueSeverity.ERROR,
            message="arith",
            field=None,
            evidence=None,
        ),
    ]
    assert outcome_from_issues(issues) == DecisionOutcome.BLOCK
