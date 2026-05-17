"""In-memory store for tracking analysis run state across async pipelines."""

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
    """Return a fresh progress dict with all pipelines set to queued/zero."""
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
    """In-memory store for active and completed analysis runs."""

    def __init__(self) -> None:
        self._runs: dict[str, RunStatusResponse] = {}
        self._lock = asyncio.Lock()

    async def create(
        self,
        run_id: str,
        progress: dict[PipelineKey, PipelineProgress] | None = None,
    ) -> None:
        """Initialise a new run entry with the given ID and optional progress state."""
        async with self._lock:
            self._runs[run_id] = RunStatusResponse(
                runId=run_id,
                status="running",
                progress=progress or empty_progress(),
            )

    async def get(self, run_id: str) -> RunStatusResponse | None:
        """Return a deep copy of the run state, or None if the run does not exist."""
        async with self._lock:
            state = self._runs.get(run_id)
            return state.model_copy(deep=True) if state is not None else None

    async def update_progress(
        self,
        run_id: str,
        key: PipelineKey,
        progress: PipelineProgress,
    ) -> None:
        """Update the progress entry for one pipeline within a run."""
        async with self._lock:
            self._runs[run_id].progress[key] = progress

    async def set_reports(  # pylint: disable=too-many-arguments
        self,
        run_id: str,
        *,
        claude_report: ModelReport | None,
        chatgpt_report: ModelReport | None,
        comparison: ComparisonReport | None,
        status: RunStatus,
    ) -> None:
        """Persist the final model reports and set the run status."""
        async with self._lock:
            state = self._runs[run_id]
            state.claudeReport = claude_report
            state.chatgptReport = chatgpt_report
            state.comparison = comparison
            state.status = status

    async def set_status(self, run_id: str, status: RunStatus) -> None:
        """Update the top-level status of a run without touching reports."""
        async with self._lock:
            self._runs[run_id].status = status


run_store = RunStore()
