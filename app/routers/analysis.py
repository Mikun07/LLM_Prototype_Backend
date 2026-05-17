"""API router for starting analysis runs and polling run status."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response, status

from app.config import Settings, get_settings
from app.models import AnalyseRequest, RunStatusResponse, StartRunResponse
from app.run_store import run_store
from app.services.analysis_service import analysis_service

router = APIRouter(tags=["analysis"])


def unavailable_providers(payload: AnalyseRequest, settings: Settings) -> list[str]:
    """Return provider names that are selected but lack a configured API key."""
    if not settings.use_real_llm:
        return []

    providers: list[str] = []
    if "claude" in payload.config.selectedModels and not settings.anthropic_api_key:
        providers.append("Claude")
    if "chatgpt" in payload.config.selectedModels and not settings.openai_api_key:
        providers.append("ChatGPT")

    return providers


@router.post("/analyse", response_model=StartRunResponse, status_code=status.HTTP_201_CREATED)
async def start_analysis(payload: AnalyseRequest, response: Response) -> StartRunResponse:
    """Validate the analysis request and start a background pipeline run."""
    if not payload.requirements:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At least one requirement is needed to start analysis.",
        )

    providers = unavailable_providers(payload, get_settings())
    if providers:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "provider_unavailable",
                "message": "Selected AI provider unavailable.",
                "providers": providers,
            },
        )

    run_id = await analysis_service.start_run(payload)
    response.headers["Location"] = f"/api/status/{run_id}"
    return StartRunResponse(runId=run_id, status="running")


@router.get("/status/{run_id}", response_model=RunStatusResponse)
async def get_run_status(run_id: str) -> RunStatusResponse:
    """Return the current progress and reports for the given run ID."""
    state = await run_store.get(run_id)
    if state is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run '{run_id}' was not found.",
        )

    return state
