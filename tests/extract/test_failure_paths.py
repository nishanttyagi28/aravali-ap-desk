from pathlib import Path

import pytest

from datasets.synth.generator import generate_dataset
from docai.contracts.truth import TruthRecord
from docai.extract import extract_file

ROOT = Path(__file__).resolve().parents[2]


def test_missing_invoice_date_low_confidence(tmp_path: Path) -> None:
    generate_dataset(50, 7, tmp_path)
    for truth_path in tmp_path.glob("*.truth.json"):
        truth = TruthRecord.model_validate_json(truth_path.read_text(encoding="utf-8"))
        if truth.invoice.invoice_date is not None:
            continue
        invoice_id = truth_path.stem.removesuffix(".truth")
        extracted = extract_file(tmp_path / f"{invoice_id}.pdf")
        assert extracted.invoice_date is None
        field = extracted.fields.get("invoice_date")
        assert field is not None
        assert field.confidence <= 0.5
        return
    pytest.fail("no missing_invoice_date case in synth seed 7")
