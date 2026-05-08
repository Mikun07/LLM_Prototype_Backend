from __future__ import annotations

import asyncio

from app.models import (
    PIPELINE_KEYS,
    ComparisonReport,
    ModelReport,
    PipelineKey,
    PipelineProgress,
    RunStatus,
    RunStatusResponse,
)


def empty_progress() -> dict[PipelineKey, PipelineProgress]:
    return {
        key: PipelineProgress(
            percentage=0,
            processed=0,
            total=0,
            status="queued",
            error=None,
        )
        for key in PIPELINE_KEYS
    }


class RunStore:
    def __init__(self) -> None:
        self._runs: dict[str, RunStatusResponse] = {}
        self._lock = asyncio.Lock()

    async def create(
        self,
        run_id: str,
        progress: dict[PipelineKey, PipelineProgress] | None = None,
    ) -> None:
        async with self._lock:
            self._runs[run_id] = RunStatusResponse(
                runId=run_id,
                status="running",
                progress=progress or empty_progress(),
            )

    async def get(self, run_id: str) -> RunStatusResponse | None:
        async with self._lock:
            state = self._runs.get(run_id)
            return state.model_copy(deep=True) if state is not None else None

    async def update_progress(
        self,
        run_id: str,
        key: PipelineKey,
        progress: PipelineProgress,
    ) -> None:
        async with self._lock:
            self._runs[run_id].progress[key] = progress

    async def set_reports(
        self,
        run_id: str,
        *,
        claude_report: ModelReport | None,
        chatgpt_report: ModelReport | None,
        comparison: ComparisonReport | None,
        status: RunStatus,
    ) -> None:
        async with self._lock:
            state = self._runs[run_id]
            state.claudeReport = claude_report
            state.chatgptReport = chatgpt_report
            state.comparison = comparison
            state.status = status

    async def set_status(self, run_id: str, status: RunStatus) -> None:
        async with self._lock:
            self._runs[run_id].status = status


run_store = RunStore()
