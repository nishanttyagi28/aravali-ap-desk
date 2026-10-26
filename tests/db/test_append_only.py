from sqlalchemy import text

from db.session import create_db_engine, init_db


def test_ledger_and_audit_append_only(tmp_path) -> None:
    url = f"sqlite:///{tmp_path / 'test.db'}"
    engine = create_db_engine(url)
    init_db(engine)
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO audit_log (event_type, message) VALUES ('test', 'hello')"))
    with engine.connect() as conn:
        try:
            conn.execute(text("UPDATE audit_log SET message = 'x' WHERE id = 1"))
            conn.commit()
            raise AssertionError("update should have failed")
        except Exception:
            pass
        try:
            conn.execute(text("DELETE FROM audit_log WHERE id = 1"))
            conn.commit()
            raise AssertionError("delete should have failed")
        except Exception:
            pass
