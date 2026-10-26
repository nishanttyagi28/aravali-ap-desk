from pathlib import Path

import pytest

pytest.importorskip("agenteval")

from datasets.synth.generator import generate_dataset
from evals.agenteval_suite import build_run_report


def test_agenteval_run_report_provenance(tmp_path: Path) -> None:
    truth_dir = tmp_path / "truth"
    generate_dataset(4, 2, truth_dir)
    run = build_run_report("truth", truth_dir)
    assert run.provenance.get("aravali") is not None
    assert run.correctness_rate is not None
    assert run.correctness_rate >= 0.99
