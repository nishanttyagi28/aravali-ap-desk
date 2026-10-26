"""FastAPI dependencies and app state."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from db.session import create_db_engine, init_db, session_factory

UPLOAD_DIR = Path("data/uploads")
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
PDF_MAGIC = b"%PDF"


class AppState:
    def __init__(
        self,
        engine: Engine,
        extract_fn: Callable[..., object] | None = None,
        vendor_master_path: Path | None = None,
    ) -> None:
        self.engine = engine
        self.session_factory = session_factory(engine)
        self.extract_fn = extract_fn
        self.vendor_master_path = vendor_master_path


def get_state(request: Request) -> AppState:
    return request.app.state.app_state


def get_db(state: Annotated[AppState, Depends(get_state)]) -> Session:
    session = state.session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def build_state(
    database_url: str | None = None,
    extract_fn: Callable[..., object] | None = None,
    vendor_master_path: Path | None = None,
) -> AppState:
    engine = create_db_engine(database_url)
    init_db(engine)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    return AppState(engine, extract_fn=extract_fn, vendor_master_path=vendor_master_path)
