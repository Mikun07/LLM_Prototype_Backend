# Backend Architecture

This document describes how the ReqSmell backend is structured, how its components
relate to each other, and why key design decisions were made the way they were.

## System Context

ReqSmell detects requirement smells in software specifications using large language models.
The backend sits between the browser and the LLM providers.

```text
Browser (React frontend)
        |
        | HTTP (JSON, multipart)
        v
  FastAPI Backend  <------>  Anthropic (Claude)
        |           HTTP      OpenAI (ChatGPT)
        |
   In-memory run store
```

The browser never calls a provider directly. API keys stay on the server side.

## Components

The backend is divided into five layers.

### 1. Entry Point

| File | Role |
|---|---|
| `Backend/main.py` | Uvicorn entry point; starts the ASGI server |
| `app/main.py` | FastAPI application factory; wires middleware, routers, and startup logging |

### 2. Routers

HTTP routing only. No business logic.

| Router | Endpoints |
|---|---|
| `app/routers/upload.py` | `POST /api/upload` |
| `app/routers/analysis.py` | `POST /api/analyse`, `GET /api/status/{run_id}` |

Each router delegates immediately to a service. Routers own status code selection and
request/response validation via Pydantic.

### 3. Services

All business logic lives in services. Each service has a single responsibility.

| Service | Responsibility |
|---|---|
| `csv_service.py` | Parses and validates an uploaded CSV file; detects column names |
| `prompt_service.py` | Builds the ambiguity and inconsistency prompt messages sent to the LLM |
| `llm_clients.py` | Calls Anthropic or OpenAI; retries transient errors; returns raw text |
| `response_parser.py` | Parses raw LLM text into structured `ParsedAmbiguity` or `ParsedInconsistency` |
| `analysis_service.py` | Orchestrates pipelines; writes progress to the run store; builds reports |
| `comparison_service.py` | Aggregates per-model results into `ModelReport` and `ComparisonReport` |

### 4. Models

`app/models.py` holds every Pydantic model used as an API contract. It is the shared
interface between routers, services, and the frontend. When a field changes here it must
also change in `Frontend/src/types/index.ts`.

### 5. Run Store

`app/run_store.py` is a plain async dictionary. It records pipeline progress and final
reports for each run ID. It does not write to disk. All state is lost when the process
restarts.

### 6. Config

`app/config.py` reads all configuration from environment variables. A single cached
`get_settings()` call is used throughout. Defaults allow the backend to start without
a `.env` file.

## Request Flow

### Upload

```text
POST /api/upload
  -> upload.py router validates file size and content type
  -> csv_service.parse_upload() reads bytes, detects columns, normalises rows
  -> UploadResponse returned with metadata, rows, and detected columns
```

### Analysis Run

```text
POST /api/analyse
  -> analysis.py router validates AnalyseRequest
  -> analysis_service.start_run() creates a run ID and writes initial progress
  -> asyncio.create_task() launches _execute_run() in the background
  -> 201 Created returned immediately with run ID and Location header

_execute_run() (background):
  for each selected (model, smell_type):
    -> _run_ambiguity_pipeline() or _run_inconsistency_pipeline()
    -> progress written to run store after each requirement or group
  -> build_model_report() aggregates results per model
  -> build_comparison_report() compares Claude and ChatGPT results
  -> run_store.set_reports() marks the run complete
```

### Status Polling

```text
GET /api/status/{run_id}
  -> run_store.get(run_id) returns current state
  -> RunStatusResponse includes progress per pipeline and reports if ready
  -> 404 if run ID does not exist
```

## Pipeline Architecture

Each pipeline combination (model x smell type) runs as an independent async task.
Failure in one pipeline does not stop the others.

| Pipeline | What it analyses | Unit of work |
|---|---|---|
| Claude + Ambiguity | Each requirement individually | 1 LLM call per requirement |
| Claude + Inconsistency | Each group of requirements together | 1 LLM call per group |
| ChatGPT + Ambiguity | Each requirement individually | 1 LLM call per requirement |
| ChatGPT + Inconsistency | Each group of requirements together | 1 LLM call per group |

Requirements are grouped by project and domain before inconsistency analysis. Groups
larger than `INCONSISTENCY_MAX_GROUP_SIZE` are chunked.

## Mock and Live Modes

The `USE_REAL_LLM` environment variable controls which path the LLM client takes.

| Mode | `USE_REAL_LLM` | Behaviour |
|---|---|---|
| Mock | `false` (default) | Returns deterministic local responses; no network calls; no API keys needed |
| Live | `true` | Calls Anthropic for Claude, OpenAI for ChatGPT; API keys required |

The Anthropic and OpenAI SDKs are imported only inside the live-mode code path. The mock
path has no dependency on them.

## Error Handling

| Situation | Behaviour |
|---|---|
| LLM call fails after retries | `ProviderRequestError` raised; pipeline marked `error`; other pipelines continue |
| LLM response cannot be parsed | `parse_error` label assigned; result still written; `WARNING` logged |
| CSV file too large | `413 Payload Too Large` returned |
| CSV has no text column | `422 Unprocessable Entity` returned |
| Run ID not found | `404 Not Found` returned |
| Provider key missing at run start | `503 Service Unavailable` returned before any pipeline starts |

## Logging

Logging is wired in `app/main.py` using `logging.basicConfig` with the level from
`LOG_LEVEL` in the environment.

| Logger | Level | Event |
|---|---|---|
| `app.services.analysis_service` | `DEBUG` | Raw LLM response text (when `LOG_RAW_LLM_RESPONSES=true`) |
| `app.services.analysis_service` | `WARNING` | Parse error for an ambiguity or inconsistency response |

## Prompt Versioning

Prompt templates in `prompt_service.py` carry a version number embedded in the system
message. The current prompt version is `2.1`. This allows LLM response behaviour to be
traced to a specific prompt, which matters when comparing results across runs.

## API Contract

The frontend and backend share a type contract. Every type in `app/models.py` has a
matching type in `Frontend/src/types/index.ts`. Changes to either file must be reflected
in both.

Key types:

| Backend (Pydantic) | Frontend (TypeScript) |
|---|---|
| `AmbiguityResult` | `AmbiguityResult` |
| `InconsistencyResult` | `InconsistencyResult` |
| `ModelReport` | `ModelReport` |
| `ComparisonReport` | `ComparisonReport` |
| `RunStatusResponse` | `RunStatusResponse` |
| `AmbiguityType` (Literal) | `AmbiguityType` (union type) |

## Known Constraints

| Constraint | Reason | Acceptable for thesis because |
|---|---|---|
| In-memory run store | Simplicity; no database dependency | Runs are short-lived; thesis context does not require persistence across restarts |
| No authentication | Thesis prototype scope | Single-user local deployment assumed |
| Single-process async | No job queue | Analysis is fast enough for the expected CSV sizes |
| No rate limiting | Thesis prototype scope | API keys are under the researcher's control |

## Dependencies

| Package | Version | Purpose |
|---|---|---|
| `fastapi` | 0.115.6 | REST API framework |
| `uvicorn[standard]` | 0.32.1 | ASGI server |
| `pydantic` | 2.10.3 | Request/response model validation |
| `python-multipart` | 0.0.19 | Multipart file upload parsing |
| `python-dotenv` | 1.0.1 | `.env` file loader |
| `anthropic` | 0.42.0 | Claude API client |
| `openai` | 1.57.4 | ChatGPT API client |

## File Map

| Change needed | Start here |
|---|---|
| Add or change an API endpoint | `app/routers/`, then `app/models.py` |
| Change CSV parsing rules | `app/services/csv_service.py` |
| Change LLM prompts | `app/services/prompt_service.py` |
| Change how LLM responses are parsed | `app/services/response_parser.py` |
| Change retry or provider call logic | `app/services/llm_clients.py` |
| Change pipeline orchestration | `app/services/analysis_service.py` |
| Change report aggregation | `app/services/comparison_service.py` |
| Change environment variables | `app/config.py`, `.env.example`, `README.md` |
| Add persistence | `app/run_store.py` |
