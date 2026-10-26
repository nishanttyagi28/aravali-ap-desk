from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from datasets.synth.generator import generate_dataset
from docai.contracts.bbox import BBox
from docai.contracts.truth import TruthRecord
from docai.extract import extract_file

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = ROOT / "datasets" / "sample"

FIELD_NAMES = [
    "invoice_number",
    "invoice_date",
    "vendor_gstin",
    "buyer_gstin",
    "place_of_supply_state_code",
    "taxable_total",
    "cgst_total",
    "sgst_total",
    "igst_total",
    "grand_total",
]


def bbox_iou(a: BBox, b: BBox) -> float:
    if a.page != b.page:
        return 0.0
    ix0 = max(a.x0, b.x0)
    iy0 = max(a.y0, b.y0)
    ix1 = min(a.x1, b.x1)
    iy1 = min(a.y1, b.y1)
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    inter = (ix1 - ix0) * (iy1 - iy0)
    union = (a.x1 - a.x0) * (a.y1 - a.y0) + (b.x1 - b.x0) * (b.y1 - b.y0) - inter
    return inter / union if union > 0 else 0.0


def _field_value_equal(expected: object, actual: object) -> bool:
    if isinstance(expected, Decimal) and isinstance(actual, Decimal):
        return expected == actual
    return expected == actual


def test_offline_accuracy_on_synth_50(tmp_path: Path) -> None:
    out = tmp_path / "synth"
    generate_dataset(50, 7, out)

    per_field_hits = dict.fromkeys(FIELD_NAMES, 0)
    line_item_hits = 0
    bbox_hits = 0
    bbox_total = 0
    n = 0

    for truth_path in sorted(out.glob("*.truth.json")):
        invoice_id = truth_path.stem.removesuffix(".truth")
        truth = TruthRecord.model_validate_json(truth_path.read_text(encoding="utf-8"))
        extracted = extract_file(out / f"{invoice_id}.pdf")

        n += 1
        if len(extracted.line_items) == len(truth.invoice.line_items):
            line_item_hits += 1

        for name in FIELD_NAMES:
            exp = getattr(truth.invoice, name)
            got = getattr(extracted, name)
            if _field_value_equal(exp, got):
                per_field_hits[name] += 1

        for key, truth_bbox in truth.bboxes.items():
            field = extracted.fields.get(key)
            if field is None or field.bbox is None:
                continue
            bbox_total += 1
            if bbox_iou(field.bbox, truth_bbox) >= 0.5:
                bbox_hits += 1

    accuracies = {k: per_field_hits[k] / n for k in FIELD_NAMES}
    line_acc = line_item_hits / n
    bbox_rate = bbox_hits / bbox_total if bbox_total else 1.0

    header = "field\taccuracy"
    rows = [header] + [f"{k}\t{accuracies[k]:.3f}" for k in FIELD_NAMES]
    rows.append(f"line_item_count\t{line_acc:.3f}")
    rows.append(f"bbox_iou>=0.5\t{bbox_rate:.3f}")
    print("\n".join(rows))

    for name in FIELD_NAMES:
        assert accuracies[name] >= 0.90, f"{name} accuracy {accuracies[name]}"
    assert line_acc >= 0.90
    assert bbox_rate >= 0.90


def test_sample_commit_accuracy() -> None:
    hits = 0
    total = 0
    for truth_path in SAMPLE.glob("*.truth.json"):
        invoice_id = truth_path.stem.removesuffix(".truth")
        truth = TruthRecord.model_validate_json(truth_path.read_text(encoding="utf-8"))
        extracted = extract_file(SAMPLE / f"{invoice_id}.pdf")
        for name in FIELD_NAMES:
            total += 1
            if getattr(truth.invoice, name) == getattr(extracted, name):
                hits += 1
    assert hits / total >= 0.90
