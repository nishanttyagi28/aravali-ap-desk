"""Synthetic / eval ground-truth record."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict

from docai.contracts.bbox import BBox
from docai.contracts.decision import DecisionOutcome
from docai.contracts.extracted import ExtractedInvoice
from docai.contracts.validation import IssueCode


class TruthRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    invoice: ExtractedInvoice
    expected_decision: DecisionOutcome
    expected_issue_codes: list[IssueCode]
    bboxes: dict[str, BBox]
    duplicate_of: UUID | None = None
