import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import yaml

from datasets.synth.generator import generate_dataset
from docai.contracts.decision import DecidedBy, Decision
from docai.contracts.truth import TruthRecord
from docai.contracts.validation import IssueSeverity, ValidationIssue
from evals.gate import gate_from_report
from evals.metrics import compute_report
from evals.run import main as run_main


def _write_pred_from_truth(
    truth_dir: Path, out_dir: Path, *, corrupt_id: str | None = None
) -> None:
    for truth_path in truth_dir.glob("*.truth.json"):
        tid = truth_path.stem.removesuffix(".truth")
        truth = TruthRecord.model_validate_json(truth_path.read_text(encoding="utf-8"))
        inv = truth.invoice
        if corrupt_id and tid == corrupt_id:
            inv = inv.model_copy(update={"invoice_number": "CORRUPT"})
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / f"{tid}.json").write_text(
            json.dumps(inv.model_dump(mode="json"), indent=2) + "\n",
            encoding="utf-8",
        )


def test_truth_as_prediction_passes_gate(tmp_path: Path) -> None:
    truth_dir = tmp_path / "truth"
    generate_dataset(10, 3, truth_dir)
    report_path = tmp_path / "report.json"
    run_main(["--pred", "truth", "--truth", str(truth_dir), "--report", str(report_path)])
    report = json.loads(report_path.read_text(encoding="utf-8"))
    thresholds = yaml.safe_load(
        (Path(__file__).resolve().parents[2] / "evals" / "thresholds.yaml").read_text()
    )
    assert gate_from_report(report, thresholds) == []


def test_corrupted_prediction_fails_named_metric(tmp_path: Path) -> None:
    truth_dir = tmp_path / "truth"
    generate_dataset(5, 11, truth_dir)
    pred_dir = tmp_path / "pred"
    manifest = json.loads((truth_dir / "manifest.json").read_text())
    corrupt_id = manifest["invoices"][0]["id"]
    _write_pred_from_truth(truth_dir, pred_dir, corrupt_id=corrupt_id)
    report = compute_report(pred_dir, truth_dir)
    thresholds = yaml.safe_load(
        (Path(__file__).resolve().parents[2] / "evals" / "thresholds.yaml").read_text()
    )
    failures = gate_from_report(report, thresholds)
    assert any("field_f1.invoice_number" in f for f in failures)


def test_decision_metrics_when_present(tmp_path: Path) -> None:
    truth_dir = tmp_path / "truth"
    generate_dataset(3, 5, truth_dir)
    pred_dir = tmp_path / "pred"
    _write_pred_from_truth(truth_dir, pred_dir)
    for truth_path in truth_dir.glob("*.truth.json"):
        tid = truth_path.stem.removesuffix(".truth")
        truth = TruthRecord.model_validate_json(truth_path.read_text(encoding="utf-8"))
        decision = Decision(
            invoice_id=UUID(tid),
            outcome=truth.expected_decision,
            issues=[
                ValidationIssue(
                    code=code,
                    severity=IssueSeverity.ERROR,
                    message=str(code),
                )
                for code in truth.expected_issue_codes
            ],
            reasons=["ok"],
            decided_by=DecidedBy.ENGINE,
            decided_at=datetime.now(UTC),
        )
        (pred_dir / f"{tid}.decision.json").write_text(
            json.dumps(decision.model_dump(mode="json"), indent=2) + "\n",
            encoding="utf-8",
        )
    report = compute_report(pred_dir, truth_dir)
    assert report["summary"]["decision_accuracy"] == 1.0
