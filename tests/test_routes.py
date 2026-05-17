"""Integration tests for the FastAPI route handlers."""
# pylint: disable=duplicate-code

from __future__ import annotations

from typing import Protocol

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import app
from app.routers import analysis as analysis_router

client = TestClient(app)


class MonkeyPatch(Protocol):  # pylint: disable=too-few-public-methods
    """Subset of pytest MonkeyPatch used in route tests."""

    def setattr(
        self,
        target: object,
        name: str,
        value: object,
        raising: bool = True,
    ) -> None:
        """Patch an attribute on a target object for the duration of the test."""


def settings_for_test(*, use_real_llm: bool) -> Settings:
    """Return a Settings object suitable for route tests with configurable LLM mode."""
    return Settings(
        use_real_llm=use_real_llm,
        anthropic_api_key=None,
        openai_api_key=None,
        claude_model="claude-test",
        openai_model="openai-test",
        llm_temperature=0.1,
        llm_max_tokens=128,
        llm_max_retries=1,
        inconsistency_max_group_size=20,
        max_csv_size_mb=10,
        backend_host="127.0.0.1",
        backend_port=8000,
        cors_origins=["http://127.0.0.1:5173"],
        log_level="INFO",
        log_raw_llm_responses=False,
        log_dir="logs",
    )


class FakeAnalysisService:  # pylint: disable=too-few-public-methods
    """Test double that returns a deterministic run id."""

    async def start_run(self, *_: object) -> str:
        """Return a fixed run ID without actually starting any pipelines."""
        return "run_test123"


def analyse_payload(*, selected_models: list[str]) -> dict[str, object]:
    """Build a minimal analyse request payload for a given set of model names."""
    return {
        "fileName": "requirements.csv",
        "requirements": [
            {
                "id": "REQ-1",
                "text": "The system shall respond quickly.",
                "domain": "Performance",
                "type": "NFR",
                "project": "Portal",
            },
        ],
        "config": {
            "temperature": 0.1,
            "maxGroupSize": 20,
            "selectedModels": selected_models,
            "selectedSmellTypes": ["ambiguity"],
        },
    }


def test_health() -> None:
    """Verify that GET /health returns status ok."""
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_upload_route() -> None:
    """Verify that POST /api/upload parses a valid CSV and returns the requirement row."""
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
    """Verify that GET /api/status with an unknown run ID returns 404."""
    response = client.get("/api/status/run_missing")

    assert response.status_code == 404


def test_start_analysis_creates_run(monkeypatch: MonkeyPatch) -> None:
    """Verify that POST /api/analyse returns 201 and a Location header for a valid request."""
    monkeypatch.setattr(
        analysis_router,
        "get_settings",
        lambda: settings_for_test(use_real_llm=False),
    )
    monkeypatch.setattr(analysis_router, "analysis_service", FakeAnalysisService())

    response = client.post(
        "/api/analyse",
        json=analyse_payload(selected_models=["chatgpt"]),
    )

    assert response.status_code == 201
    assert response.headers["location"] == "/api/status/run_test123"
    assert response.json() == {"runId": "run_test123", "status": "running"}


def test_start_analysis_returns_503_when_provider_key_is_missing(
    monkeypatch: MonkeyPatch,
) -> None:
    """Verify that POST /api/analyse returns 503 when a selected provider has no API key."""
    monkeypatch.setattr(
        analysis_router,
        "get_settings",
        lambda: settings_for_test(use_real_llm=True),
    )
    monkeypatch.setattr(analysis_router, "analysis_service", FakeAnalysisService())

    response = client.post(
        "/api/analyse",
        json=analyse_payload(selected_models=["claude"]),
    )

    assert response.status_code == 503
    detail = response.json()["detail"]
    assert detail["code"] == "provider_unavailable"
    assert detail["message"] == "Selected AI provider unavailable."
    assert detail["providers"] == ["Claude"]
    assert "API_KEY" not in str(detail)
    assert "configured" not in str(detail).lower()
