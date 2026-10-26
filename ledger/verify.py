"""CLI: python -m ledger.verify [--db <url or path>]"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from db.session import create_db_engine, init_db
from ledger.posting import verify_receipt_chain


def _resolve_db_url(arg: str) -> str:
    if "://" in arg:
        return arg
    path = Path(arg)
    return f"sqlite:///{path.resolve()}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify ledger receipt hash chain")
    parser.add_argument(
        "--db",
        default="data/ap_desk.db",
        help="SQLite path or SQLAlchemy URL (default: data/ap_desk.db)",
    )
    args = parser.parse_args(argv)

    engine = create_db_engine(_resolve_db_url(args.db))
    init_db(engine)
    with engine.connect() as conn:
        from sqlalchemy.orm import Session

        with Session(bind=conn) as session:
            broken = verify_receipt_chain(session)
    if broken is None:
        print("OK: receipt chain verified")
        return 0
    print(f"BROKEN: receipt chain failed at seq={broken}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
