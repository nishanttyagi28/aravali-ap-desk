from __future__ import annotations

from docai.contracts.extracted import ExtractedInvoice
from docai.contracts.validation import IssueCode, IssueSeverity, ValidationIssue
from docai.validate.util import key_field_names

_CONFIDENCE_THRESHOLD = 0.80


def check_low_confidence(inv: ExtractedInvoice) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for name in key_field_names():
        field = inv.fields.get(name)
        if field is None:
            continue
        if field.confidence < _CONFIDENCE_THRESHOLD:
            issues.append(
                ValidationIssue(
                    code=IssueCode.LOW_CONFIDENCE,
                    severity=IssueSeverity.WARN,
                    field=name,
                    message=f"Low extraction confidence for {name}",
                    evidence={"confidence": field.confidence},
                )
            )
    return issues
