from __future__ import annotations

import asyncio
from collections import defaultdict
from uuid import uuid4

from app.config import get_settings
from app.models import (
    AmbiguityResult,
    AnalyseRequest,
    ConfidenceLevel,
    InconsistencyResult,
    ModelName,
    ModelReport,
    PipelineKey,
    PipelineProgress,
    PipelineStatus,
    RequirementRow,
    SmellType,
    pipeline_key,
)
from app.run_store import RunStore, run_store
from app.services.comparison_service import build_comparison_report, build_model_report
from app.services.llm_clients import LlmClient
from app.services.prompt_service import build_ambiguity_prompt, build_inconsistency_prompt
from app.services.response_parser import (
    ParsedInconsistencyPair,
    parse_ambiguity_response,
    parse_inconsistency_response,
)

ALL_MODELS: tuple[ModelName, ...] = ("claude", "chatgpt")
ALL_SMELL_TYPES: tuple[SmellType, ...] = ("ambiguity", "inconsistency")


def confidence_for_parse_error() -> ConfidenceLevel:
    return "LOW"


def as_object_rows(rows: list[AmbiguityResult] | list[InconsistencyResult]) -> list[object]:
    return list(rows)


def selected_pipeline_keys(request: AnalyseRequest) -> list[PipelineKey]:
    return [
        pipeline_key(model, smell_type)
        for model in request.config.selectedModels
        for smell_type in request.config.selectedSmellTypes
    ]


def progress(
    processed: int,
    total: int,
    status: PipelineStatus,
    error: str | None = None,
) -> PipelineProgress:
    if total == 0 and status == "complete":
        percentage = 100
    else:
        percentage = int((processed / max(total, 1)) * 100)

    return PipelineProgress(
        percentage=min(100, percentage),
        processed=processed,
        total=total,
        status=status,
        error=error,
    )


def normalise_group_key(row: RequirementRow) -> tuple[str, str]:
    return (row.project.strip() or "Default", row.domain.strip() or "General")


def chunked(rows: list[RequirementRow], size: int) -> list[list[RequirementRow]]:
    return [rows[index : index + size] for index in range(0, len(rows), size)]


def group_requirements(
    rows: list[RequirementRow],
    max_group_size: int,
) -> list[list[RequirementRow]]:
    grouped: dict[tuple[str, str], list[RequirementRow]] = defaultdict(list)
    for row in rows:
        grouped[normalise_group_key(row)].append(row)

    groups: list[list[RequirementRow]] = []
    for group_rows in grouped.values():
        if len(group_rows) < 2:
            continue
        groups.extend(chunked(group_rows, max(2, max_group_size)))
        # groups.append(group_rows)

    return groups


def candidate_pairs(
    group: list[RequirementRow],
) -> list[tuple[RequirementRow, RequirementRow]]:
    pairs: list[tuple[RequirementRow, RequirementRow]] = []

    for first_index in range(len(group)):
        for second_index in range(first_index + 1, len(group)):
            pairs.append(
                (
                    group[first_index],
                    group[second_index],
                )
            )

    return pairs


def pair_lookup(rows: list[RequirementRow]) -> dict[str, RequirementRow]:
    return {row.id: row for row in rows}


def result_from_parsed_pair(
    parsed_pair: ParsedInconsistencyPair,
    requirements_by_id: dict[str, RequirementRow],
) -> InconsistencyResult | None:
    first = requirements_by_id.get(parsed_pair.req_a_id)
    second = requirements_by_id.get(parsed_pair.req_b_id)
    if first is None or second is None:
        return None

    return InconsistencyResult(
        reqAId=first.id,
        reqBId=second.id,
        reqAText=first.text,
        reqBText=second.text,
        domain=first.domain,
        project=first.project,
        label="SMELL" if parsed_pair.label != "consistent" else "CLEAN",
        confidence=parsed_pair.confidence,
        explanation=parsed_pair.explanation,
        suggestion=parsed_pair.suggestion,
    )


def clean_pair_result(first: RequirementRow, second: RequirementRow) -> InconsistencyResult:
    return InconsistencyResult(
        reqAId=first.id,
        reqBId=second.id,
        reqAText=first.text,
        reqBText=second.text,
        domain=first.domain,
        project=first.project,
        label="CLEAN",
        confidence="LOW",
        explanation="No contradiction was detected for this candidate pair.",
        suggestion="",
    )


class AnalysisService:
    def __init__(self, store: RunStore, llm_client: LlmClient | None = None) -> None:
        self._store = store
        self._llm_client = llm_client or LlmClient()

    async def start_run(self, request: AnalyseRequest) -> str:
        run_id = f"run_{uuid4().hex[:12]}"
        await self._store.create(run_id, self._initial_progress(request))
        asyncio.create_task(self._execute_run(run_id, request))
        return run_id

    def _initial_progress(self, request: AnalyseRequest) -> dict[PipelineKey, PipelineProgress]:
        groups = group_requirements(request.requirements, request.config.maxGroupSize)
        state: dict[PipelineKey, PipelineProgress] = {}
        for model in ALL_MODELS:
            for smell_type in ALL_SMELL_TYPES:
                key = pipeline_key(model, smell_type)
                is_selected = (
                    model in request.config.selectedModels
                    and smell_type in request.config.selectedSmellTypes
                )
                total = len(request.requirements) if smell_type == "ambiguity" else len(groups)
                state[key] = progress(0, total if is_selected else 0, "queued")

        return state

    async def _execute_run(self, run_id: str, request: AnalyseRequest) -> None:
        results: dict[ModelName, dict[SmellType, list[object]]] = {
            "claude": {"ambiguity": [], "inconsistency": []},
            "chatgpt": {"ambiguity": [], "inconsistency": []},
        }
        tasks = [
            self._run_pipeline(run_id, request, model, smell_type)
            for model in request.config.selectedModels
            for smell_type in request.config.selectedSmellTypes
        ]

        gathered = await asyncio.gather(*tasks, return_exceptions=True)
        for item in gathered:
            if isinstance(item, BaseException):
                continue
            model, smell_type, rows = item
            results[model][smell_type] = rows

        claude_report = self._report_for_model("claude", request, results)
        chatgpt_report = self._report_for_model("chatgpt", request, results)
        comparison = (
            build_comparison_report(request.fileName, claude_report, chatgpt_report)
            if claude_report is not None and chatgpt_report is not None
            else None
        )
        current = await self._store.get(run_id)
        selected_keys = selected_pipeline_keys(request)
        has_pipeline_error = current is not None and any(
            current.progress[key].status == "error" for key in selected_keys
        )
        await self._store.set_reports(
            run_id,
            claude_report=claude_report,
            chatgpt_report=chatgpt_report,
            comparison=comparison,
            status="error" if has_pipeline_error else "complete",
        )

    def _report_for_model(
        self,
        model: ModelName,
        request: AnalyseRequest,
        results: dict[ModelName, dict[SmellType, list[object]]],
    ) -> ModelReport | None:
        if model not in request.config.selectedModels:
            return None

        ambiguity_results = [
            row for row in results[model]["ambiguity"] if isinstance(row, AmbiguityResult)
        ]
        inconsistency_results = [
            row for row in results[model]["inconsistency"] if isinstance(row, InconsistencyResult)
        ]
        return build_model_report(
            model,
            request.fileName,
            ambiguity_results,
            inconsistency_results,
        )

    async def _run_pipeline(
        self,
        run_id: str,
        request: AnalyseRequest,
        model: ModelName,
        smell_type: SmellType,
    ) -> tuple[ModelName, SmellType, list[object]]:
        key = pipeline_key(model, smell_type)
        try:
            if smell_type == "ambiguity":
                ambiguity_rows = await self._run_ambiguity_pipeline(
                    run_id,
                    key,
                    model,
                    request.requirements,
                )
                return model, smell_type, as_object_rows(ambiguity_rows)

            inconsistency_rows = await self._run_inconsistency_pipeline(
                run_id,
                key,
                model,
                request.requirements,
                request.config.maxGroupSize,
            )
            return model, smell_type, as_object_rows(inconsistency_rows)
        except Exception as exc:
            current = await self._store.get(run_id)
            total = current.progress[key].total if current is not None else 0
            await self._store.update_progress(run_id, key, progress(0, total, "error", str(exc)))
            return model, smell_type, []

    async def _run_ambiguity_pipeline(
        self,
        run_id: str,
        key: PipelineKey,
        model: ModelName,
        requirements: list[RequirementRow],
    ) -> list[AmbiguityResult]:
        total = len(requirements)
        await self._store.update_progress(run_id, key, progress(0, total, "running"))
        rows: list[AmbiguityResult] = []
        for index, requirement in enumerate(requirements, start=1):
            prompt = build_ambiguity_prompt(requirement)
            raw = await self._llm_client.complete_with_retries(model, prompt)
            parsed = parse_ambiguity_response(raw)
            rows.append(
                AmbiguityResult(
                    id=requirement.id,
                    text=requirement.text,
                    domain=requirement.domain,
                    type=requirement.type,
                    label="SMELL" if parsed.label in {"ambiguous", "parse_error"} else "CLEAN",
                    confidence=parsed.confidence,
                    explanation=parsed.explanation,
                    suggestion=parsed.suggestion,
                ),
            )
            await self._store.update_progress(run_id, key, progress(index, total, "running"))

        await self._store.update_progress(run_id, key, progress(total, total, "complete"))
        return rows

    async def _run_inconsistency_pipeline(
        self,
        run_id: str,
        key: PipelineKey,
        model: ModelName,
        requirements: list[RequirementRow],
        max_group_size: int,
    ) -> list[InconsistencyResult]:
        groups = group_requirements(requirements, max_group_size)
        requirements_by_id = pair_lookup(requirements)
        total = len(groups)
        await self._store.update_progress(run_id, key, progress(0, total, "running"))
        rows: list[InconsistencyResult] = []

        for index, group in enumerate(groups, start=1):
            project_name = (
                group[0].project.strip() if group and group[0].project else "Unknown Project"
            )
            prompt = build_inconsistency_prompt(
                project_name,
                group,
            )
            raw = await self._llm_client.complete_with_retries(model, prompt)
            parsed = parse_inconsistency_response(raw)
            smell_pairs = [
                result
                for pair in parsed.pairs
                if (result := result_from_parsed_pair(pair, requirements_by_id)) is not None
            ]
            # if smell_pairs:
            #    rows.extend(smell_pairs)
            # else:
            #    rows.extend(
            #       clean_pair_result(first, second) for first, second in candidate_pairs(group)
            #  )

            detected_keys = {tuple(sorted([row.reqAId, row.reqBId])) for row in smell_pairs}
            # Add all detected inconsistency rows
            rows.extend(smell_pairs)
            # Add CLEAN rows for all remaining pairs
            for first, second in candidate_pairs(group):
                pair_key = tuple(sorted([first.id, second.id]))
                if pair_key not in detected_keys:
                    rows.append(clean_pair_result(first, second))

            await self._store.update_progress(run_id, key, progress(index, total, "running"))

        await self._store.update_progress(run_id, key, progress(total, total, "complete"))
        return rows


analysis_service = AnalysisService(run_store, LlmClient(get_settings()))
