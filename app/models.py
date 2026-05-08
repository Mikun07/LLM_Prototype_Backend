from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ModelName = Literal["claude", "chatgpt"]
SmellType = Literal["ambiguity", "inconsistency"]
RequirementType = str
SmellLabel = Literal["SMELL", "CLEAN"]
ConfidenceLevel = Literal["HIGH", "MEDIUM", "LOW"]
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
    return ["claude", "chatgpt"]


def default_smell_types() -> list[SmellType]:
    return ["ambiguity", "inconsistency"]


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FileMetadata(ApiModel):
    name: str
    size: int
    rowCount: int


class ColumnDetection(ApiModel):
    id: bool
    text: bool
    domain: bool
    type: bool
    project: bool


class RequirementRow(ApiModel):
    id: str
    text: str
    domain: str = "General"
    type: RequirementType = "UNKNOWN"
    project: str = "Default"


class UploadResponse(ApiModel):
    file: FileMetadata
    requirements: list[RequirementRow]
    detectedColumns: list[str]
    detection: ColumnDetection


class RunConfig(ApiModel):
    temperature: float = Field(default=0.1, ge=0.0, le=1.0)
    maxGroupSize: int = Field(default=20, ge=2, le=200)
    selectedModels: list[ModelName] = Field(default_factory=default_models)
    selectedSmellTypes: list[SmellType] = Field(default_factory=default_smell_types)


class AnalyseRequest(ApiModel):
    requirements: list[RequirementRow]
    config: RunConfig = Field(default_factory=RunConfig)
    fileName: str = "uploaded-requirements.csv"


class StartRunResponse(ApiModel):
    runId: str
    status: RunStatus


class PipelineProgress(ApiModel):
    percentage: int
    processed: int
    total: int
    status: PipelineStatus
    error: str | None = None


class BreakdownValue(ApiModel):
    name: str
    total: int
    smells: int
    clean: int
    smellRate: float


class ReportStats(ApiModel):
    total: int
    smells: int
    clean: int
    smellRate: float
    bySmellType: list[BreakdownValue]
    byDomain: list[BreakdownValue]
    byRequirementType: list[BreakdownValue]


class AmbiguityResult(ApiModel):
    id: str
    text: str
    domain: str
    type: RequirementType
    label: SmellLabel
    confidence: ConfidenceLevel
    explanation: str
    suggestion: str = ""


class InconsistencyResult(ApiModel):
    reqAId: str
    reqBId: str
    reqAText: str
    reqBText: str
    domain: str
    label: SmellLabel
    confidence: ConfidenceLevel
    explanation: str
    suggestion: str = ""


class ModelReport(ApiModel):
    model: ModelName
    generatedAt: str
    fileName: str
    stats: ReportStats
    ambiguityResults: list[AmbiguityResult]
    inconsistencyResults: list[InconsistencyResult]


class ComparisonStats(ApiModel):
    fullAgreement: int
    claudeOnly: int
    chatgptOnly: int
    bothClean: int
    agreementRate: float
    bySmellType: list[BreakdownValue]
    byDomain: list[BreakdownValue]


class ComparisonRow(ApiModel):
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
    generatedAt: str
    fileName: str
    stats: ComparisonStats
    rows: list[ComparisonRow]


class RunStatusResponse(ApiModel):
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
    if model == "claude" and smell_type == "ambiguity":
        return "claudeAmbiguity"
    if model == "claude" and smell_type == "inconsistency":
        return "claudeInconsistency"
    if model == "chatgpt" and smell_type == "ambiguity":
        return "chatgptAmbiguity"

    return "chatgptInconsistency"
