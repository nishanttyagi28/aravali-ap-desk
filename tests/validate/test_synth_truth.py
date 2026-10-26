import json
from pathlib import Path

from datasets.synth.generator import generate_dataset
from docai.contracts.truth import TruthRecord
from docai.contracts.vendor import VendorMaster
from docai.validate import build_history_from_manifest, decide, validate


def test_synthetic_truth_issues_and_decisions(tmp_path: Path) -> None:
    generate_dataset(50, 7, tmp_path)
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    master = VendorMaster.model_validate_json((tmp_path / "vendor_master.json").read_text())

    seen: list[tuple] = []
    for entry in manifest["invoices"]:
        tid = entry["id"]
        truth = TruthRecord.model_validate_json((tmp_path / f"{tid}.truth.json").read_text())
        history = build_history_from_manifest(seen)
        issues = validate(
            truth.invoice,
            master,
            history,
            duplicate_of=truth.duplicate_of,
        )
        assert {issue.code for issue in issues} == set(truth.expected_issue_codes)
        decision = decide(issues, truth.invoice)
        assert decision.outcome == truth.expected_decision
        seen.append((truth.invoice, truth.duplicate_of))
