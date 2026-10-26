"""CLI: python -m datasets.synth --n 50 --seed 7 --out datasets/generated"""

from __future__ import annotations

import argparse
from pathlib import Path

from datasets.synth.generator import generate_dataset


def main() -> None:
    parser = argparse.ArgumentParser(description="Synthetic GST invoice generator v0")
    parser.add_argument("--n", type=int, required=True, help="Number of invoices")
    parser.add_argument("--seed", type=int, required=True, help="RNG seed")
    parser.add_argument("--out", type=Path, required=True, help="Output directory")
    args = parser.parse_args()
    generate_dataset(args.n, args.seed, args.out)
    print(f"Wrote {args.n} invoices to {args.out}")


if __name__ == "__main__":
    main()
