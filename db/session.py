"""Database engine and session factory."""

from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from db.models import Base, SchemaVersion

DEFAULT_URL = "sqlite:///data/aravali.db"
APP_SCHEMA_VERSION = 1


def database_url() -> str:
    return os.environ.get("DATABASE_URL", DEFAULT_URL)


def _sqlite_path(url: str) -> Path | None:
    if url.startswith("sqlite:///"):
        raw = url.removeprefix("sqlite:///")
        return Path(raw)
    return None


def create_db_engine(url: str | None = None) -> Engine:
    resolved = url or database_url()
    connect_args = {"check_same_thread": False} if resolved.startswith("sqlite") else {}
    return create_engine(resolved, connect_args=connect_args)


def _install_append_only_triggers(connection) -> None:  # noqa: ANN001
    connection.execute(
        text(
            """
            CREATE TRIGGER IF NOT EXISTS ledger_entries_no_update
            BEFORE UPDATE ON ledger_entries
            BEGIN
                SELECT RAISE(ABORT, 'ledger_entries is append-only');
            END;
            """
        )
    )
    connection.execute(
        text(
            """
            CREATE TRIGGER IF NOT EXISTS ledger_entries_no_delete
            BEFORE DELETE ON ledger_entries
            BEGIN
                SELECT RAISE(ABORT, 'ledger_entries is append-only');
            END;
            """
        )
    )
    connection.execute(
        text(
            """
            CREATE TRIGGER IF NOT EXISTS audit_log_no_update
            BEFORE UPDATE ON audit_log
            BEGIN
                SELECT RAISE(ABORT, 'audit_log is append-only');
            END;
            """
        )
    )
    connection.execute(
        text(
            """
            CREATE TRIGGER IF NOT EXISTS audit_log_no_delete
            BEFORE DELETE ON audit_log
            BEGIN
                SELECT RAISE(ABORT, 'audit_log is append-only');
            END;
            """
        )
    )
    connection.execute(
        text(
            """
            CREATE TRIGGER IF NOT EXISTS ledger_receipts_no_update
            BEFORE UPDATE ON ledger_receipts
            BEGIN
                SELECT RAISE(ABORT, 'ledger_receipts is append-only');
            END;
            """
        )
    )
    connection.execute(
        text(
            """
            CREATE TRIGGER IF NOT EXISTS ledger_receipts_no_delete
            BEFORE DELETE ON ledger_receipts
            BEGIN
                SELECT RAISE(ABORT, 'ledger_receipts is append-only');
            END;
            """
        )
    )


def init_db(engine: Engine) -> None:
    path = _sqlite_path(str(engine.url))
    if path is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(engine)
    if str(engine.url).startswith("sqlite"):
        with engine.begin() as conn:
            _install_append_only_triggers(conn)
    with Session(engine) as session:
        row = session.get(SchemaVersion, APP_SCHEMA_VERSION)
        if row is None:
            session.add(SchemaVersion(version=APP_SCHEMA_VERSION))
            session.commit()


def session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_session(engine: Engine) -> Generator[Session, None, None]:
    factory = session_factory(engine)
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def assert_append_only(engine: Engine, table: str, operation: str) -> bool:
    """Return True if raw SQL mutation is rejected (SQLite triggers)."""
    with engine.connect() as conn:
        try:
            if operation == "update":
                conn.execute(text(f"UPDATE {table} SET message = message WHERE 0"))
            else:
                conn.execute(text(f"DELETE FROM {table} WHERE 0"))
            conn.commit()
            return False
        except Exception:
            return True
