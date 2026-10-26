import json
import subprocess
import sys
from pathlib import Path

from pypdf import PdfReader

from datasets.synth.generator import BROKEN_CASES, CLEAN_CASES, generate_dataset
from docai.contracts.gstin import is_valid_gstin
from docai.contracts.truth import TruthRecord
from docai.contracts.validation import IssueCode
from docai.contracts.vendor import VendorMaster

ROOT = Path(__file__).resolve().parents[2]
CLEAN_SET = set(CLEAN_CASES)


def test_generator_count_and_determinism(tmp_path: Path) -> None:
    out1 = tmp_path / "run1"
    out2 = tmp_path / "run2"
    generate_dataset(50, 7, out1)
    generate_dataset(50, 7, out2)
    truths1 = sorted(out1.glob("*.truth.json"))
    truths2 = sorted(out2.glob("*.truth.json"))
    assert len(truths1) == 50
    assert len(truths2) == 50
    for a, b in zip(truths1, truths2, strict=True):
        assert a.read_text(encoding="utf-8") == b.read_text(encoding="utf-8")


def test_truth_validates_and_clean_arithmetic(tmp_path: Path) -> None:
    generate_dataset(50, 7, tmp_path)
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    master = VendorMaster.model_validate_json((tmp_path / "vendor_master.json").read_text())
    seen_broken: set[str] = set()
    prior_by_id: dict[str, dict] = {}

    for entry in manifest["invoices"]:
        tid = entry["id"]
        prior_by_id[tid] = entry
        truth = TruthRecord.model_validate_json((tmp_path / f"{tid}.truth.json").read_text())
        case = entry["case"]
        inv = truth.invoice
        gstin = inv.vendor_gstin or ""

        if case in CLEAN_SET:
            assert truth.expected_issue_codes == []
            assert is_valid_gstin(gstin)
            line_sum = sum(li.total for li in inv.line_items)
            assert inv.grand_total == line_sum
        else:
            assert truth.expected_issue_codes != []
            seen_broken.add(case)

        if case == "bad_gstin_checksum":
            assert not is_valid_gstin(gstin)
        elif case == "gstin_state_mismatch":
            assert is_valid_gstin(gstin)
            assert IssueCode.GSTIN_STATE_MISMATCH in truth.expected_issue_codes
            vendor = master.lookup_by_gstin(gstin)
            if vendor is not None:
                assert gstin[:2].upper() != vendor.state_code
        elif case != "unknown_vendor":
            assert is_valid_gstin(gstin)

        if case == "unknown_vendor":
            assert master.lookup_by_gstin(gstin) is None

        if case == "duplicate_invoice":
            assert truth.duplicate_of is not None
            orig = prior_by_id.get(str(truth.duplicate_of))
            assert orig is not None
            orig_truth = TruthRecord.model_validate_json(
                (tmp_path / f"{truth.duplicate_of}.truth.json").read_text()
            )
            assert orig_truth.invoice.vendor_gstin == inv.vendor_gstin
            assert orig_truth.invoice.invoice_number == inv.invoice_number

        pdf = tmp_path / f"{tid}.pdf"
        reader = PdfReader(str(pdf))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        assert inv.invoice_number in text

    assert seen_broken == set(BROKEN_CASES)


def test_cli_module(tmp_path: Path) -> None:
    subprocess.check_call(
        [sys.executable, "-m", "datasets.synth", "--n", "3", "--seed", "1", "--out", str(tmp_path)],
        cwd=ROOT,
    )
    assert len(list(tmp_path.glob("*.pdf"))) == 3
