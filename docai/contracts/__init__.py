"""Pydantic v2 contracts (frozen after M1)."""

from docai.contracts.bbox import BBox
from docai.contracts.decision import DecidedBy, Decision, DecisionOutcome
from docai.contracts.errors import ErrorResponse
from docai.contracts.extracted import (
    ALLOWED_GST_RATES,
    ExtractedField,
    ExtractedInvoice,
    ExtractionMode,
    FieldSource,
    LineItem,
)
from docai.contracts.ledger import LedgerEntry, SealRef, WitnessStatus
from docai.contracts.metrics import Metrics
from docai.contracts.review import ReviewAction, ReviewActionType, ReviewQueueItem, ReviewResult
from docai.contracts.truth import TruthRecord
from docai.contracts.validation import IssueCode, IssueSeverity, ValidationIssue
from docai.contracts.vendor import InvoiceHistory, InvoiceHistoryRecord, Vendor, VendorMaster

__all__ = [
    "ALLOWED_GST_RATES",
    "BBox",
    "DecidedBy",
    "Decision",
    "DecisionOutcome",
    "ErrorResponse",
    "ExtractedField",
    "ExtractedInvoice",
    "ExtractionMode",
    "FieldSource",
    "InvoiceHistory",
    "InvoiceHistoryRecord",
    "IssueCode",
    "IssueSeverity",
    "LedgerEntry",
    "LineItem",
    "Metrics",
    "ReviewAction",
    "ReviewActionType",
    "ReviewQueueItem",
    "ReviewResult",
    "SealRef",
    "TruthRecord",
    "ValidationIssue",
    "Vendor",
    "VendorMaster",
    "WitnessStatus",
]
