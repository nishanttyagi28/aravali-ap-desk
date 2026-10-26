"""CLI: python -m datasets.synth --n 50 --seed 7 --out datasets/generated"""

from __future__ import annotations

import argparse
from pathlib import Path

from datasets.synth.generator import SynthOptions, generate_dataset


def main() -> None:
    parser = argparse.ArgumentParser(description="Synthetic GST invoice generator")
    parser.add_argument("--n", type=int, required=True, help="Number of invoices")
    parser.add_argument("--seed", type=int, required=True, help="RNG seed")
    parser.add_argument("--out", type=Path, required=True, help="Output directory")
    parser.add_argument(
        "--template",
        choices=["classic", "compact"],
        default=None,
        help="Layout template (v1; omit for v0-compatible classic)",
    )
    parser.add_argument(
        "--scanned-ratio",
        type=float,
        default=0.0,
        help="Fraction of invoices rasterised to scanned image PDFs (v1)",
    )
    parser.add_argument(
        "--multipage",
        action="store_true",
        help="Emit multi-page invoices with line items spilling to page 2 (v1)",
    )
    args = parser.parse_args()
    if args.scanned_ratio < 0 or args.scanned_ratio > 1:
        raise SystemExit("--scanned-ratio must be between 0 and 1")
    options = SynthOptions(
        template=args.template,
        scanned_ratio=args.scanned_ratio,
        multipage=args.multipage,
    )
    generate_dataset(args.n, args.seed, args.out, options=options)
    print(f"Wrote {args.n} invoices to {args.out}")


if __name__ == "__main__":
    main()
