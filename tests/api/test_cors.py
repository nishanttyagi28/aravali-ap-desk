from pathlib import Path

from fastapi.testclient import TestClient

from api.deps import build_state
from api.main import create_app


def test_cors_preflight_allows_vite_origin(tmp_path: Path) -> None:
    state = build_state(database_url=f"sqlite:///{tmp_path / 'cors.db'}")
    client = TestClient(create_app(state))
    resp = client.options(
        "/invoices",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:5173"
