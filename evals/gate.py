"""CLI: python -m evals.gate [--report path] [--thresholds path]"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

_DEFAULT_REPORT = Path("evals/out/report.json")
_DEFAULT_THRESHOLDS = Path("evals/thresholds.yaml")


def _check_floor(name: str, value: float | None, floor: float, failures: list[str]) -> None:
    if value is None:
        failures.append(f"{name}: no value (missing data)")
        return
    if value < floor:
        failures.append(f"{name}: {value:.4f} < {floor:.4f}")


def gate_from_report(report: dict, thresholds: dict) -> list[str]:
    failures: list[str] = []
    summary = report.get("summary") or {}
    header = summary.get("header_fields") or {}

    field_min = float(thresholds["header_field_f1_min"])
    for field_name, scores in header.items():
        _check_floor(f"field_f1.{field_name}", scores.get("f1"), field_min, failures)

    _check_floor(
        "header_macro_f1",
        summary.get("header_macro_f1"),
        float(thresholds["header_macro_f1_min"]),
        failures,
    )
    line = summary.get("line_items") or {}
    _check_floor(
        "line_items_f1",
        line.get("f1"),
        float(thresholds["line_items_f1_min"]),
        failures,
    )
    bboxes = summary.get("bboxes") or {}
    _check_floor(
        "bbox_iou_at_0_5",
        bboxes.get("iou_at_0_5_rate"),
        float(thresholds["bbox_iou_at_0_5_min"]),
        failures,
    )

    dec_count = summary.get("decision_count") or 0
    if dec_count > 0:
        _check_floor(
            "decision_accuracy",
            summary.get("decision_accuracy"),
            float(thresholds["decision_accuracy_min"]),
            failures,
        )

    missing = report.get("missing_predictions") or []
    if missing:
        failures.append(f"missing_predictions: {len(missing)} invoice(s)")

    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fail if eval metrics are below thresholds")
    parser.add_argument("--report", type=Path, default=_DEFAULT_REPORT)
    parser.add_argument("--thresholds", type=Path, default=_DEFAULT_THRESHOLDS)
    args = parser.parse_args(argv)

    if not args.report.is_file():
        print(f"Report not found: {args.report}", file=sys.stderr)
        return 1

    thresholds = yaml.safe_load(args.thresholds.read_text(encoding="utf-8"))
    report = json.loads(args.report.read_text(encoding="utf-8"))
    failures = gate_from_report(report, thresholds)

    if failures:
        print("Eval gate FAILED:", file=sys.stderr)
        for line in failures:
            print(f"  - {line}", file=sys.stderr)
        return 1

    print("Eval gate passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
