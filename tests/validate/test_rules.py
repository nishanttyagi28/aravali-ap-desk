"""Focused validation rule tests (HSN, buyer GSTIN, round-off)."""

from decimal import Decimal

from datasets.synth.generator import generate_dataset
from docai.contracts.decision import DecisionOutcome
from docai.contracts.truth import TruthRecord
from docai.contracts.validation import IssueCode, IssueSeverity
from docai.contracts.vendor import VendorMaster
from docai.validate import build_history_from_manifest, decide, validate
from docai.validate.rules.gstin import check_gstin_checksum
from docai.validate.rules.missing import check_missing_fields
from docai.validate.rules.round_off import check_round_off


def _clean_truth(tmp_path) -> TruthRecord:
    generate_dataset(1, 3, tmp_path, cases_override=["clean_intrastate"])
    return TruthRecord.model_validate_json(next(tmp_path.glob("*.truth.json")).read_text())


def test_missing_hsn_sac_issues_missing_field(tmp_path) -> None:
    truth = _clean_truth(tmp_path)
    inv = truth.invoice.model_copy(
        update={
            "line_items": [
                line.model_copy(update={"hsn_sac": None}) for line in truth.invoice.line_items
            ]
        }
    )
    issues = check_missing_fields(inv)
    assert any(
        issue.code == IssueCode.MISSING_FIELD and issue.field == "line_items[0].hsn_sac"
        for issue in issues
    )
    assert all(
        issue.severity == IssueSeverity.WARN
        for issue in issues
        if issue.code == IssueCode.MISSING_FIELD
    )

    master = VendorMaster.model_validate_json((tmp_path / "vendor_master.json").read_text())
    all_issues = validate(inv, master, build_history_from_manifest([]))
    decision = decide(all_issues, inv)
    assert decision.outcome == DecisionOutcome.REVIEW


def test_invalid_buyer_gstin_emits_gstin_checksum(tmp_path) -> None:
    truth = _clean_truth(tmp_path)
    inv = truth.invoice.model_copy(update={"buyer_gstin": "27AAAAA0000A1Z0"})
    issues = check_gstin_checksum(inv)
    assert len(issues) == 1
    issue = issues[0]
    assert issue.code == IssueCode.GSTIN_CHECKSUM
    assert issue.field == "buyer_gstin"
    assert issue.severity == IssueSeverity.ERROR


def test_round_off_exceeded_when_abs_greater_than_one(tmp_path) -> None:
    truth = _clean_truth(tmp_path)
    inv = truth.invoice.model_copy(update={"round_off": Decimal("1.50")})
    issues = check_round_off(inv)
    assert len(issues) == 1
    issue = issues[0]
    assert issue.code == IssueCode.ROUND_OFF_EXCEEDED
    assert issue.field == "round_off"
    assert issue.severity == IssueSeverity.WARN
