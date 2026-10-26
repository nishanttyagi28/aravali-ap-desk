"""CLI: python -m evals.run --pred <dir|truth> --truth <dir> --report <path>"""

from __future__ import annotations

import argparse
from pathlib import Path

from evals.metrics import compute_report, write_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run AP Desk extraction evaluation")
    parser.add_argument("--pred", required=True, help="Prediction directory or 'truth'")
    parser.add_argument("--truth", type=Path, required=True, help="Truth directory (*.truth.json)")
    parser.add_argument("--report", type=Path, required=True, help="Output report JSON path")
    args = parser.parse_args(argv)

    pred: Path | str = args.pred if args.pred == "truth" else Path(args.pred)
    report = compute_report(pred, args.truth)
    write_report(report, args.report)
    print(f"Wrote report for {report['summary'].get('count', 0)} invoices to {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
