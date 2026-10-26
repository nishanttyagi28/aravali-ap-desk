"""Validation issue contracts."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict


class IssueCode(StrEnum):
    GSTIN_CHECKSUM = "GSTIN_CHECKSUM"
    GSTIN_STATE_MISMATCH = "GSTIN_STATE_MISMATCH"
    TAX_REGIME_MISMATCH = "TAX_REGIME_MISMATCH"
    LINE_ARITHMETIC = "LINE_ARITHMETIC"
    TOTAL_MISMATCH = "TOTAL_MISMATCH"
    DUPLICATE_INVOICE = "DUPLICATE_INVOICE"
    VENDOR_UNKNOWN = "VENDOR_UNKNOWN"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    MISSING_FIELD = "MISSING_FIELD"
    ROUND_OFF_EXCEEDED = "ROUND_OFF_EXCEEDED"


class IssueSeverity(StrEnum):
    INFO = "info"
    WARN = "warn"
    ERROR = "error"


class ValidationIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: IssueCode
    severity: IssueSeverity
    field: str | None = None
    message: str
    evidence: dict[str, Any] | None = None
