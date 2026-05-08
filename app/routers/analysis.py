from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.models import AnalyseRequest, RunStatusResponse, StartRunResponse
from app.run_store import run_store
from app.services.analysis_service import analysis_service

router = APIRouter(tags=["analysis"])


@router.post("/analyse", response_model=StartRunResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_analysis(payload: AnalyseRequest) -> StartRunResponse:
    if not payload.requirements:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At least one requirement is needed to start analysis.",
        )

    run_id = await analysis_service.start_run(payload)
    return StartRunResponse(runId=run_id, status="running")


@router.get("/status/{run_id}", response_model=RunStatusResponse)
async def get_run_status(run_id: str) -> RunStatusResponse:
    state = await run_store.get(run_id)
    if state is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run '{run_id}' was not found.",
        )

    return state
