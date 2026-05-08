from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_upload_route() -> None:
    csv_bytes = (
        b"id,text,domain,type,project\n" b"REQ-1,The system shall respond quickly,Auth,NFR,Portal\n"
    )

    response = client.post(
        "/api/upload",
        files={
            "file": (
                "requirements.csv",
                csv_bytes,
                "text/csv",
            ),
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["file"]["rowCount"] == 1
    assert body["requirements"][0]["id"] == "REQ-1"


def test_unknown_status_route() -> None:
    response = client.get("/api/status/run_missing")

    assert response.status_code == 404
