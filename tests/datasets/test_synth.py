import json
import subprocess
import sys
from pathlib import Path

import pytest
from pypdf import PdfReader

from datasets.synth.generator import (
    BROKEN_CASES,
    BROKEN_CASES_V1,
    CLEAN_CASES,
    GENERATOR_VERSION,
    SynthOptions,
    generate_dataset,
)
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


def test_v0_manifest_version_and_pdf_bytes_deterministic(tmp_path: Path) -> None:
    out = tmp_path / "v0"
    manifest = generate_dataset(50, 7, out)
    assert manifest["generator_version"] == GENERATOR_VERSION
    blobs = sorted(p.read_bytes() for p in out.glob("*.pdf"))
    assert len(blobs) == 50
    out2 = tmp_path / "v0b"
    generate_dataset(50, 7, out2)
    blobs2 = sorted(p.read_bytes() for p in out2.glob("*.pdf"))
    assert blobs == blobs2


def test_v1_flags_bump_generator_version(tmp_path: Path) -> None:
    manifest = generate_dataset(
        5,
        1,
        tmp_path,
        options=SynthOptions(template="compact"),
    )
    assert manifest["generator_version"] == "synth-v1"


def test_v1_broken_cases_validate_where_supported(tmp_path: Path) -> None:
    from docai.contracts.gstin import is_valid_gstin
    from docai.contracts.vendor import VendorMaster
    from docai.validate import build_history_from_manifest, decide, validate

    for case in BROKEN_CASES_V1:
        out = tmp_path / case
        generate_dataset(1, 1, out, cases_override=[case], options=SynthOptions(template="classic"))
        truth = TruthRecord.model_validate_json(
            next(out.glob("*.truth.json")).read_text(encoding="utf-8")
        )
        master = VendorMaster.model_validate_json((out / "vendor_master.json").read_text())
        issues = validate(truth.invoice, master, build_history_from_manifest([]))
        codes = {i.code for i in issues}
        if case == "buyer_gstin_checksum":
            assert not is_valid_gstin(truth.invoice.buyer_gstin or "")
            assert IssueCode.GSTIN_CHECKSUM in codes
        elif case == "round_off_exceeded":
            assert IssueCode.ROUND_OFF_EXCEEDED in codes
            assert truth.expected_decision == truth.expected_decision
        elif case == "hsn_missing":
            assert truth.invoice.line_items[0].hsn_sac is None
            assert IssueCode.MISSING_FIELD in truth.expected_issue_codes
            continue
        decision = decide(issues, truth.invoice)
        assert {c for c in truth.expected_issue_codes}.issubset(codes)
        assert decision.outcome == truth.expected_decision


def test_scanned_pdf_is_image_only(tmp_path: Path) -> None:
    pytest.importorskip("pypdfium2")
    pytest.importorskip("PIL")
    out = tmp_path / "scanned"
    generate_dataset(
        3,
        9,
        out,
        options=SynthOptions(scanned_ratio=1.0),
    )
    for pdf in out.glob("*.pdf"):
        reader = PdfReader(str(pdf))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        assert text.strip() == ""


def test_multipage_invoices(tmp_path: Path) -> None:
    out = tmp_path / "multi"
    generate_dataset(2, 4, out, options=SynthOptions(multipage=True))
    for truth_path in out.glob("*.truth.json"):
        truth = TruthRecord.model_validate_json(truth_path.read_text(encoding="utf-8"))
        assert truth.invoice.page_count >= 2


def test_cli_module(tmp_path: Path) -> None:
    subprocess.check_call(
        [sys.executable, "-m", "datasets.synth", "--n", "3", "--seed", "1", "--out", str(tmp_path)],
        cwd=ROOT,
    )
    assert len(list(tmp_path.glob("*.pdf"))) == 3
