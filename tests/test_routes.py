from __future__ import annotations

from typing import Protocol

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import app
from app.routers import analysis as analysis_router

client = TestClient(app)


class MonkeyPatch(Protocol):
    def setattr(
        self,
        target: object,
        name: str,
        value: object,
        raising: bool = True,
    ) -> None: ...


def settings_for_test(*, use_real_llm: bool) -> Settings:
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


class FakeAnalysisService:
    async def start_run(self, payload: object) -> str:
        return "run_test123"


def analyse_payload(*, selected_models: list[str]) -> dict[str, object]:
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


def test_start_analysis_creates_run(monkeypatch: MonkeyPatch) -> None:
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
