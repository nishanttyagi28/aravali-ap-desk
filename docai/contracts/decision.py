"""Decision contract."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from docai.contracts.validation import ValidationIssue


class DecisionOutcome(StrEnum):
    ALLOW = "ALLOW"
    REVIEW = "REVIEW"
    BLOCK = "BLOCK"


class DecidedBy(StrEnum):
    ENGINE = "engine"
    HUMAN = "human"


class Decision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    invoice_id: UUID
    outcome: DecisionOutcome
    issues: list[ValidationIssue]
    reasons: list[str]
    decided_by: DecidedBy
    decided_at: datetime
