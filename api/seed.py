"""Idempotent local DB seed: vendor master + sample invoices."""

from __future__ import annotations

import json
import os
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from api.deps import UPLOAD_DIR, build_state
from api.services import ensure_vendors, ingest_upload
from db.models import InvoiceRow
from docai.extract import extract_file

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DIR = ROOT / "datasets" / "sample"


def seed_sample_invoices(session: Session, state, *, sample_dir: Path = SAMPLE_DIR) -> int:
    """Upload each sample PDF if not already present (by sha256). Returns upload count."""
    master_path = sample_dir / "vendor_master.json"
    master = ensure_vendors(session, master_path)
    manifest_path = sample_dir / "manifest.json"
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        ids = [entry["id"] for entry in manifest.get("invoices", [])]
    else:
        ids = [p.stem.removesuffix(".truth") for p in sample_dir.glob("*.truth.json")]

    uploaded = 0
    for iid in ids:
        pdf = sample_dir / f"{iid}.pdf"
        if not pdf.is_file():
            continue
        content = pdf.read_bytes()
        digest = __import__("hashlib").sha256(content).hexdigest()
        existing = session.scalars(
            select(InvoiceRow).where(InvoiceRow.sha256 == digest).limit(1)
        ).first()
        if existing is not None:
            continue
        ingest_upload(
            session,
            content,
            pdf.name,
            state.extract_fn or extract_file,
            master,
            UPLOAD_DIR,
        )
        uploaded += 1
    return uploaded


def main() -> None:
    db_url = os.environ.get("DATABASE_URL", "sqlite:///data/ap_desk.db")
    state = build_state(
        database_url=db_url,
        vendor_master_path=SAMPLE_DIR / "vendor_master.json",
    )
    session = state.session_factory()
    try:
        n = seed_sample_invoices(session, state)
        session.commit()
        print(f"Seed complete ({n} new uploads from {SAMPLE_DIR.name})")
    finally:
        session.close()


if __name__ == "__main__":
    main()
