"""Pydantic models, type aliases, and enumerations for the ReqSmell API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

ModelName = Literal["claude", "chatgpt"]
SmellType = Literal["ambiguity", "inconsistency"]
RequirementType = str
SmellLabel = Literal["SMELL", "CLEAN"]
ConfidenceLevel = Literal["HIGH", "MEDIUM", "LOW"]
AmbiguityType = Literal["lexical", "syntactic", "referential", "semantic", "none"]
AgreementStatus = Literal["AGREE", "DISAGREE"]
PipelineStatus = Literal["queued", "running", "complete", "error"]
RunStatus = Literal["running", "complete", "error"]
PipelineKey = Literal[
    "claudeAmbiguity",
    "claudeInconsistency",
    "chatgptAmbiguity",
    "chatgptInconsistency",
]


def default_models() -> list[ModelName]:
    """Return the default list of model names used when none are specified."""
    return ["claude", "chatgpt"]


def default_smell_types() -> list[SmellType]:
    """Return the default list of smell types used when none are specified."""
    return ["ambiguity", "inconsistency"]


class ApiModel(BaseModel):
    """Base API model that rejects unexpected fields."""

    model_config = ConfigDict(extra="forbid")


class FileMetadata(ApiModel):
    """Metadata describing an uploaded requirements file."""

    name: str
    size: int
    rowCount: int


class ColumnDetection(ApiModel):
    """Column detection result for an uploaded CSV file."""

    id: bool
    text: bool
    domain: bool
    type: bool
    project: bool


class RequirementRow(ApiModel):
    """Single requirement row parsed from an uploaded file."""

    id: str
    text: str
    domain: str = "General"
    type: RequirementType = "UNKNOWN"
    project: str = "Default"


class UploadResponse(ApiModel):
    """Response returned after a successful CSV upload."""

    file: FileMetadata
    requirements: list[RequirementRow]
    detectedColumns: list[str]
    detection: ColumnDetection


class RunConfig(ApiModel):
    """Configuration values used to start an analysis run."""

    temperature: float = Field(default=0.1, ge=0.0, le=1.0)
    maxGroupSize: int = Field(default=20, ge=2, le=200)
    selectedModels: list[ModelName] = Field(default_factory=default_models)
    selectedSmellTypes: list[SmellType] = Field(default_factory=default_smell_types)

    @field_validator("selectedModels", "selectedSmellTypes")
    @classmethod
    def require_at_least_one_selection(cls, value: list[str]) -> list[str]:
        """Require at least one selected model and smell type for a runnable analysis."""
        if not value:
            raise ValueError("At least one option must be selected.")

        return value


class AnalyseRequest(ApiModel):
    """Request body for starting an analysis run."""

    requirements: list[RequirementRow]
    config: RunConfig = Field(default_factory=RunConfig)
    fileName: str = "uploaded-requirements.csv"


class StartRunResponse(ApiModel):
    """Response returned when an analysis run is created."""

    runId: str
    status: RunStatus


class PipelineProgress(ApiModel):
    """Progress state for one model and smell-type pipeline."""

    percentage: int
    processed: int
    total: int
    status: PipelineStatus
    error: str | None = None


class BreakdownValue(ApiModel):
    """Aggregated clean and smell counts for one report group."""

    name: str
    total: int
    smells: int
    clean: int
    smellRate: float


class ReportStats(ApiModel):
    """Aggregate statistics included in each model report."""

    total: int
    smells: int
    clean: int
    smellRate: float
    bySmellType: list[BreakdownValue]
    byDomain: list[BreakdownValue]
    byRequirementType: list[BreakdownValue]


class AmbiguityResult(ApiModel):
    """Analysis result for one ambiguity check."""

    id: str
    text: str
    domain: str
    type: RequirementType
    label: SmellLabel
    confidence: ConfidenceLevel
    ambiguityType: AmbiguityType = "none"
    explanation: str
    suggestion: str = ""


class InconsistencyResult(ApiModel):
    """Analysis result for one inconsistency pair check."""

    reqAId: str
    reqBId: str
    reqAText: str
    reqBText: str
    domain: str
    project: str
    label: SmellLabel
    confidence: ConfidenceLevel
    explanation: str
    suggestion: str = ""


class ModelReport(ApiModel):
    """Complete smell-analysis report for one model."""

    model: ModelName
    generatedAt: str
    fileName: str
    stats: ReportStats
    ambiguityResults: list[AmbiguityResult]
    inconsistencyResults: list[InconsistencyResult]


class ComparisonStats(ApiModel):
    """Aggregate agreement statistics across model reports."""

    fullAgreement: int
    claudeOnly: int
    chatgptOnly: int
    bothClean: int
    agreementRate: float
    bySmellType: list[BreakdownValue]
    byDomain: list[BreakdownValue]


class ComparisonRow(ApiModel):
    """Side-by-side model labels for one compared requirement."""

    id: str
    text: str
    domain: str
    type: RequirementType
    smellType: SmellType
    claudeLabel: SmellLabel
    claudeConfidence: ConfidenceLevel
    chatgptLabel: SmellLabel
    chatgptConfidence: ConfidenceLevel
    agreementStatus: AgreementStatus


class ComparisonReport(ApiModel):
    """Complete comparison report for Claude and ChatGPT."""

    generatedAt: str
    fileName: str
    stats: ComparisonStats
    rows: list[ComparisonRow]


class RunStatusResponse(ApiModel):
    """Stored and returned state for an analysis run."""

    runId: str
    status: RunStatus
    progress: dict[PipelineKey, PipelineProgress]
    claudeReport: ModelReport | None = None
    chatgptReport: ModelReport | None = None
    comparison: ComparisonReport | None = None


PIPELINE_KEYS: tuple[PipelineKey, ...] = (
    "claudeAmbiguity",
    "claudeInconsistency",
    "chatgptAmbiguity",
    "chatgptInconsistency",
)


def pipeline_key(model: ModelName, smell_type: SmellType) -> PipelineKey:
    """Map a model and smell type to the corresponding pipeline key."""
    if model == "claude" and smell_type == "ambiguity":
        return "claudeAmbiguity"
    if model == "claude" and smell_type == "inconsistency":
        return "claudeInconsistency"
    if model == "chatgpt" and smell_type == "ambiguity":
        return "chatgptAmbiguity"

    return "chatgptInconsistency"
