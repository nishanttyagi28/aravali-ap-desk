from pathlib import Path

from fastapi.testclient import TestClient

from api.deps import build_state
from api.main import create_app


def test_error_response_shapes(tmp_path: Path) -> None:
    state = build_state(database_url=f"sqlite:///{tmp_path / 'err.db'}")
    client = TestClient(create_app(state))
    missing = client.get(f"/invoices/{'00000000-0000-0000-0000-000000000001'}")
    assert missing.status_code == 404
    body = missing.json()
    assert body["code"] == "not_found"
    assert "message" in body

    big = client.post(
        "/invoices",
        files={"file": ("big.pdf", b"%PDF" + b"x" * (10 * 1024 * 1024 + 1), "application/pdf")},
    )
    assert big.status_code == 413
    assert big.json()["code"] == "payload_too_large"

    bad_type = client.post("/invoices", files={"file": ("x.txt", b"not-a-pdf", "text/plain")})
    assert bad_type.status_code == 415
    assert bad_type.json()["code"] == "unsupported_media_type"

    invalid_review = client.post(
        "/invoices/00000000-0000-0000-0000-000000000001/review",
        json={"action": "approve"},
    )
    assert invalid_review.status_code == 422
    assert invalid_review.json()["code"] == "validation_error"
