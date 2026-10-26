"""GST validation engine (M2 — agent B)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from docai.contracts.decision import DecidedBy, Decision
from docai.contracts.extracted import ExtractedInvoice
from docai.contracts.validation import IssueCode, ValidationIssue
from docai.contracts.vendor import InvoiceHistory, InvoiceHistoryRecord, VendorMaster
from docai.validate import rules
from docai.validate.policy import outcome_from_issues
from docai.validate.util import financial_year, normalise_invoice_number

__all__ = ["validate", "decide", "build_history_from_manifest"]


def build_history_from_manifest(
    invoices: list[tuple[ExtractedInvoice, UUID | None]],
) -> InvoiceHistory:
    """Build duplicate index in manifest order; ``duplicate_of`` marks duplicate rows only."""
    records: list[InvoiceHistoryRecord] = []
    for inv, duplicate_of in invoices:
        if duplicate_of is not None:
            continue
        if not inv.vendor_gstin or not inv.invoice_number or inv.invoice_date is None:
            continue
        records.append(
            InvoiceHistoryRecord(
                vendor_gstin=inv.vendor_gstin,
                normalised_invoice_number=normalise_invoice_number(inv.invoice_number),
                financial_year=financial_year(inv.invoice_date),
                invoice_id=inv.invoice_id,
            )
        )
    return InvoiceHistory(records=records)


def validate(
    inv: ExtractedInvoice,
    vendors: VendorMaster,
    history: InvoiceHistory,
    *,
    duplicate_of: UUID | None = None,
) -> list[ValidationIssue]:
    is_dup = duplicate_of is not None
    issues: list[ValidationIssue] = []
    issues.extend(rules.check_missing_fields(inv))
    issues.extend(rules.check_gstin_checksum(inv))
    issues.extend(rules.check_gstin_state(inv, vendors))
    issues.extend(rules.check_vendor(inv, vendors))
    vendor_unknown = any(issue.code == IssueCode.VENDOR_UNKNOWN for issue in issues)
    issues.extend(rules.check_duplicate(inv, history, is_duplicate_case=is_dup))
    line_issues = rules.check_line_arithmetic(inv)
    issues.extend(line_issues)
    has_line_arith = any(issue.code == IssueCode.LINE_ARITHMETIC for issue in line_issues)
    total_issues: list[ValidationIssue] = []
    if not has_line_arith:
        total_issues = rules.check_totals(inv)
        issues.extend(total_issues)
    has_total_mismatch = any(issue.code == IssueCode.TOTAL_MISMATCH for issue in total_issues)
    if (
        not is_dup
        and not vendor_unknown
        and inv.invoice_date is not None
        and not has_line_arith
        and not has_total_mismatch
    ):
        issues.extend(rules.check_tax_regime(inv))
    issues.extend(rules.check_round_off(inv))
    issues.extend(rules.check_low_confidence(inv))
    return _dedupe_issues(issues)


def decide(issues: list[ValidationIssue], inv: ExtractedInvoice) -> Decision:
    outcome = outcome_from_issues(issues)
    reasons = [issue.message for issue in issues] if issues else ["No validation issues"]
    return Decision(
        invoice_id=inv.invoice_id,
        outcome=outcome,
        issues=issues,
        reasons=reasons,
        decided_by=DecidedBy.ENGINE,
        decided_at=datetime.now(UTC),
    )


def _dedupe_issues(issues: list[ValidationIssue]) -> list[ValidationIssue]:
    seen: set[tuple[IssueCode, str | None]] = set()
    out: list[ValidationIssue] = []
    for issue in issues:
        key = (issue.code, issue.field)
        if key in seen:
            continue
        seen.add(key)
        out.append(issue)
    return out
