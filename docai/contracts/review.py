"""Human review contracts."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from docai.contracts.decision import Decision, DecisionOutcome
from docai.contracts.extracted import ExtractedInvoice
from docai.contracts.validation import IssueCode


class ReviewActionType(StrEnum):
    APPROVE = "approve"
    CORRECT = "correct"
    REJECT = "reject"


class ReviewAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: ReviewActionType
    corrections: dict[str, Any] | None = None
    reviewer: str


class ReviewQueueItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    invoice_id: UUID
    vendor_name: str | None = None
    vendor_gstin: str | None = None
    invoice_number: str | None = None
    invoice_date: date | None = None
    grand_total: Decimal
    outcome: DecisionOutcome
    top_issue_code: IssueCode | None = None
    issue_count: int = Field(ge=0)
    posted: bool = False


class ReviewResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: Decision
    invoice: ExtractedInvoice
