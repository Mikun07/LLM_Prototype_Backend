"""Builds model and comparison reports from analysis results."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime

from app.models import (
    AgreementStatus,
    AmbiguityResult,
    BreakdownValue,
    ComparisonReport,
    ComparisonRow,
    ComparisonStats,
    InconsistencyResult,
    ModelName,
    ModelReport,
    ReportStats,
    SmellLabel,
)


def percentage(part: int, total: int) -> float:
    """Return part/total as a rounded percentage, or 0 when total is zero."""
    return 0 if total == 0 else round((part / total) * 100, 1)


def build_breakdowns(rows: list[tuple[str, SmellLabel]]) -> list[BreakdownValue]:
    """Aggregate (name, label) pairs into sorted BreakdownValue counts."""
    grouped: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "smells": 0})
    for name, label in rows:
        grouped[name]["total"] += 1
        grouped[name]["smells"] += 1 if label == "SMELL" else 0

    return [
        BreakdownValue(
            name=name,
            total=value["total"],
            smells=value["smells"],
            clean=value["total"] - value["smells"],
            smellRate=percentage(value["smells"], value["total"]),
        )
        for name, value in sorted(grouped.items())
    ]


def build_stats(
    ambiguity_results: list[AmbiguityResult],
    inconsistency_results: list[InconsistencyResult],
) -> ReportStats:
    """Compute aggregate smell statistics from ambiguity and inconsistency results."""
    smell_rows: list[tuple[str, str, str, SmellLabel]] = [
        ("Ambiguity", row.domain, row.type, row.label) for row in ambiguity_results
    ]
    smell_rows.extend(
        ("Inconsistency", row.domain, "Pair", row.label) for row in inconsistency_results
    )
    total = len(smell_rows)
    smells = sum(1 for *_, label in smell_rows if label == "SMELL")

    return ReportStats(
        total=total,
        smells=smells,
        clean=total - smells,
        smellRate=percentage(smells, total),
        bySmellType=build_breakdowns([(row[0], row[3]) for row in smell_rows]),
        byDomain=build_breakdowns([(row[1], row[3]) for row in smell_rows]),
        byRequirementType=build_breakdowns([(row[2], row[3]) for row in smell_rows]),
    )


def build_model_report(
    model: ModelName,
    file_name: str,
    ambiguity_results: list[AmbiguityResult],
    inconsistency_results: list[InconsistencyResult],
) -> ModelReport:
    """Assemble a complete ModelReport from analysis results for one model."""
    return ModelReport(
        model=model,
        generatedAt=datetime.now(UTC).isoformat(),
        fileName=file_name,
        stats=build_stats(ambiguity_results, inconsistency_results),
        ambiguityResults=ambiguity_results,
        inconsistencyResults=inconsistency_results,
    )


def _ambiguity_comparison_rows(
    claude_report: ModelReport,
    chatgpt_report: ModelReport,
) -> list[ComparisonRow]:
    chatgpt_by_id = {row.id: row for row in chatgpt_report.ambiguityResults}
    rows: list[ComparisonRow] = []
    for claude_row in claude_report.ambiguityResults:
        chatgpt_row = chatgpt_by_id.get(claude_row.id)
        if chatgpt_row is None:
            continue

        agreement_status: AgreementStatus = (
            "AGREE" if claude_row.label == chatgpt_row.label else "DISAGREE"
        )
        rows.append(
            ComparisonRow(
                id=claude_row.id,
                text=claude_row.text,
                domain=claude_row.domain,
                type=claude_row.type,
                smellType="ambiguity",
                claudeLabel=claude_row.label,
                claudeConfidence=claude_row.confidence,
                chatgptLabel=chatgpt_row.label,
                chatgptConfidence=chatgpt_row.confidence,
                agreementStatus=agreement_status,
            ),
        )

    return rows


def _inconsistency_comparison_rows(
    claude_report: ModelReport,
    chatgpt_report: ModelReport,
) -> list[ComparisonRow]:
    chatgpt_by_id = {
        f"{row.reqAId}/{row.reqBId}": row for row in chatgpt_report.inconsistencyResults
    }
    rows: list[ComparisonRow] = []
    for claude_row in claude_report.inconsistencyResults:
        row_id = f"{claude_row.reqAId}/{claude_row.reqBId}"
        chatgpt_row = chatgpt_by_id.get(row_id)
        if chatgpt_row is None:
            continue

        agreement_status: AgreementStatus = (
            "AGREE" if claude_row.label == chatgpt_row.label else "DISAGREE"
        )
        rows.append(
            ComparisonRow(
                id=row_id,
                text=f"{claude_row.reqAText} / {claude_row.reqBText}",
                domain=claude_row.domain,
                type="Pair",
                smellType="inconsistency",
                claudeLabel=claude_row.label,
                claudeConfidence=claude_row.confidence,
                chatgptLabel=chatgpt_row.label,
                chatgptConfidence=chatgpt_row.confidence,
                agreementStatus=agreement_status,
            ),
        )

    return rows


def build_comparison_report(
    file_name: str,
    claude_report: ModelReport,
    chatgpt_report: ModelReport,
) -> ComparisonReport:
    """Build a side-by-side ComparisonReport from Claude and ChatGPT model reports."""
    rows = [
        *_ambiguity_comparison_rows(claude_report, chatgpt_report),
        *_inconsistency_comparison_rows(claude_report, chatgpt_report),
    ]
    full_agreement = sum(1 for row in rows if row.agreementStatus == "AGREE")
    both_clean = sum(
        1 for row in rows if row.claudeLabel == "CLEAN" and row.chatgptLabel == "CLEAN"
    )
    claude_only = sum(
        1 for row in rows if row.claudeLabel == "SMELL" and row.chatgptLabel == "CLEAN"
    )
    chatgpt_only = sum(
        1 for row in rows if row.claudeLabel == "CLEAN" and row.chatgptLabel == "SMELL"
    )

    return ComparisonReport(
        generatedAt=datetime.now(UTC).isoformat(),
        fileName=file_name,
        stats=ComparisonStats(
            fullAgreement=full_agreement,
            claudeOnly=claude_only,
            chatgptOnly=chatgpt_only,
            bothClean=both_clean,
            agreementRate=percentage(full_agreement, len(rows)),
            bySmellType=build_breakdowns(
                [
                    (row.smellType, "CLEAN" if row.agreementStatus == "AGREE" else "SMELL")
                    for row in rows
                ],
            ),
            byDomain=build_breakdowns(
                [
                    (row.domain, "CLEAN" if row.agreementStatus == "AGREE" else "SMELL")
                    for row in rows
                ],
            ),
        ),
        rows=rows,
    )
