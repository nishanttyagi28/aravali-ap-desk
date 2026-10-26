"""Export Pydantic contract models to JSON Schema files under schemas/."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from docai.contracts.bbox import BBox
from docai.contracts.decision import Decision
from docai.contracts.errors import ErrorResponse
from docai.contracts.extracted import ExtractedField, ExtractedInvoice, LineItem
from docai.contracts.ledger import LedgerEntry, SealRef
from docai.contracts.metrics import Metrics
from docai.contracts.review import ReviewAction, ReviewQueueItem, ReviewResult
from docai.contracts.truth import TruthRecord
from docai.contracts.validation import ValidationIssue
from docai.contracts.vendor import InvoiceHistory, InvoiceHistoryRecord, Vendor, VendorMaster

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCHEMAS_DIR = ROOT / "schemas"

MODELS: list[tuple[str, type]] = [
    ("BBox", BBox),
    ("ExtractedField", ExtractedField),
    ("LineItem", LineItem),
    ("ExtractedInvoice", ExtractedInvoice),
    ("ValidationIssue", ValidationIssue),
    ("Decision", Decision),
    ("ReviewAction", ReviewAction),
    ("ReviewQueueItem", ReviewQueueItem),
    ("ReviewResult", ReviewResult),
    ("LedgerEntry", LedgerEntry),
    ("SealRef", SealRef),
    ("Metrics", Metrics),
    ("ErrorResponse", ErrorResponse),
    ("Vendor", Vendor),
    ("VendorMaster", VendorMaster),
    ("InvoiceHistory", InvoiceHistory),
    ("InvoiceHistoryRecord", InvoiceHistoryRecord),
    ("TruthRecord", TruthRecord),
]


def export_to(schemas_dir: Path) -> None:
    schemas_dir.mkdir(parents=True, exist_ok=True)
    index: dict[str, str] = {}
    for name, model in MODELS:
        schema = model.model_json_schema(mode="serialization")
        schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
        schema["title"] = name
        path = schemas_dir / f"{name}.schema.json"
        text = json.dumps(schema, indent=2, sort_keys=True) + "\n"
        path.write_text(text, encoding="utf-8")
        index[name] = f"{name}.schema.json"
    index_path = schemas_dir / "index.json"
    index_path.write_text(json.dumps(index, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Export contract JSON Schemas")
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_SCHEMAS_DIR,
        help="Output directory (default: schemas/)",
    )
    args = parser.parse_args()
    export_to(args.out.resolve())
    return 0


if __name__ == "__main__":
    sys.exit(main())
