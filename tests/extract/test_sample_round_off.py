"""Offline extract + validate for sample round_off_exceeded invoice."""

from pathlib import Path

from docai.contracts.decision import DecisionOutcome
from docai.contracts.truth import TruthRecord
from docai.contracts.validation import IssueCode
from docai.contracts.vendor import VendorMaster
from docai.extract import extract_file
from docai.validate import build_history_from_manifest, decide, validate

ROOT = Path(__file__).resolve().parents[2]
SAMPLE_ID = "11ce5dd2-b45e-d1f0-3139-d32c93cd59bf"
SAMPLE_DIR = ROOT / "datasets" / "sample"


def test_sample_round_off_exceeded_offline_pipeline() -> None:
    truth = TruthRecord.model_validate_json(
        (SAMPLE_DIR / f"{SAMPLE_ID}.truth.json").read_text(encoding="utf-8")
    )
    master = VendorMaster.model_validate_json(
        (SAMPLE_DIR / "vendor_master.json").read_text(encoding="utf-8")
    )
    inv = extract_file(SAMPLE_DIR / f"{SAMPLE_ID}.pdf")

    assert inv.invoice_number == truth.invoice.invoice_number
    assert inv.round_off == truth.invoice.round_off

    issues = validate(inv, master, build_history_from_manifest([]))
    codes = {i.code for i in issues}
    assert IssueCode.ROUND_OFF_EXCEEDED in codes
    assert IssueCode.TOTAL_MISMATCH not in codes

    decision = decide(issues, inv)
    assert decision.outcome == DecisionOutcome.REVIEW
    assert decision.outcome == truth.expected_decision
