"""Write ExtractedInvoice + Decision predictions via offline extract + validate."""

from __future__ import annotations

import json
from pathlib import Path

from docai.contracts.vendor import VendorMaster
from docai.extract import extract_file
from docai.validate import build_history_from_manifest, decide, validate


def predict_directory(
    truth_dir: Path, pred_dir: Path, *, vendor_master: Path | None = None
) -> None:
    pred_dir.mkdir(parents=True, exist_ok=True)
    master_path = vendor_master or truth_dir / "vendor_master.json"
    master = VendorMaster.model_validate_json(master_path.read_text(encoding="utf-8"))
    seen: list[tuple] = []
    for truth_path in sorted(truth_dir.glob("*.truth.json")):
        iid = truth_path.stem.removesuffix(".truth")
        pdf = truth_dir / f"{iid}.pdf"
        inv = extract_file(pdf)
        (pred_dir / f"{iid}.json").write_text(
            json.dumps(inv.model_dump(mode="json"), indent=2) + "\n",
            encoding="utf-8",
        )
        history = build_history_from_manifest(seen)
        issues = validate(inv, master, history)
        decision = decide(issues, inv)
        (pred_dir / f"{iid}.decision.json").write_text(
            json.dumps(decision.model_dump(mode="json"), indent=2) + "\n",
            encoding="utf-8",
        )
        seen.append((inv, None))
