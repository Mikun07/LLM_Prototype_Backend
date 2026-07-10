# ReqSmell Backend

FastAPI backend for the ReqSmell requirements smell detection prototype.

This backend is the intended service version of the earlier
`genai-requirements-smells` experiment. The script pipeline has been reorganised into
API routes, Pydantic models, services, an in-memory run store, and testable parsing logic.

## Related Repositories

| Repository | Purpose |
|---|---|
| [ReqSmell Frontend](https://github.com/Mikun07/LLM_Prototype_Frontend) | React client for upload, configuration, progress polling, and report review |
| [ReqSmell Backend](https://github.com/Mikun07/LLM_Prototype_Backend) | This FastAPI API |

## What It Provides

| Endpoint | Purpose |
|---|---|
| `GET /health` | Basic server health check; returns `200 OK` when reachable |
| `POST /api/upload` | Upload, validate, parse, and preview a CSV file; returns `200 OK` on success |
| `POST /api/analyse` | Create an analysis run; returns `201 Created` with a `Location` header |
| `GET /api/status/{run_id}` | Poll progress and retrieve reports; returns `200 OK` for known runs |

## Status Handling

| Status | Where it appears | Meaning |
|---|---|---|
| `200 OK` | Health, upload, status polling | The request succeeded |
| `201 Created` | Analysis start | A new run was created and can be polled through the `Location` header |
| `404 Not Found` | Status polling | The requested run ID does not exist |
| `413 Payload Too Large` | Upload | The CSV file is larger than the configured limit |
| `422 Unprocessable Entity` | Upload or analysis start | The request body or CSV content is invalid |
| `503 Service Unavailable` | Analysis start | A selected live model provider is missing required API configuration |

The API response shapes are designed to match the current React frontend contract in
`Frontend/src/types/index.ts`.

## Documentation

| Document | Purpose |
|---|---|
| [Architecture](docs/ARCHITECTURE.md) | Component structure, request flow, design decisions |
| [Command Reference](docs/COMMANDS.md) | Setup, run, test, and version commands |
| [Versioning Guide](docs/VERSIONING.md) | Backend version policy and release workflow |
| [Requirements](docs/REQUIREMENTS.md) | Problem statement, user stories, functional and non-functional requirements, traceability |
| [Risk Assessment](docs/RISK_ASSESSMENT.md) | Technical, security, operational, and project risks with mitigations |
| [Security](docs/SECURITY.md) | Threat model, asset identification, attack surface, secure coding requirements |
| [DevOps](docs/DEVOPS.md) | Environment strategy, build pipeline, configuration, logging, incident management |
| [Version Index](docs/versions/index.md) | List of released backend versions |
| [v1.0.0 Baseline](docs/versions/v1/v1.0.0.md) | Current backend baseline document |

## Runtime Modes

| Mode | Setting | Behaviour |
|---|---|---|
| Mock mode | `USE_REAL_LLM=false` | No external API calls; deterministic local responses |
| Live mode | `USE_REAL_LLM=true` | Calls Anthropic for Claude and OpenAI for ChatGPT |

Mock mode is the default so the backend can be developed and tested without API keys.

## Setup

```powershell
cd Backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -m uvicorn app.main:app --reload --port 8000
```

Open the API docs:

```text
http://127.0.0.1:8000/docs
```

The frontend Vite proxy already targets `http://localhost:8000`.

## Environment

All configuration is loaded from `.env` (copy `.env.example` to get started):

| Variable | Default | Purpose |
|---|---|---|
| `USE_REAL_LLM` | `false` | `true` makes live provider calls; `false` uses deterministic mock |
| `ANTHROPIC_API_KEY` | _(empty)_ | Required when Claude is selected and `USE_REAL_LLM=true` |
| `OPENAI_API_KEY` | _(empty)_ | Required when ChatGPT is selected and `USE_REAL_LLM=true` |
| `CLAUDE_MODEL` | `claude-sonnet-4-20250514` | Anthropic model identifier |
| `OPENAI_MODEL` | `gpt-4o` | OpenAI model identifier |
| `LLM_TEMPERATURE` | `0.1` | Sampling temperature (0.0 – 1.0) |
| `LLM_MAX_TOKENS` | `2048` | Max tokens per LLM response |
| `LLM_MAX_RETRIES` | `3` | Retry attempts on transient provider errors |
| `INCONSISTENCY_MAX_GROUP_SIZE` | `20` | Max requirements per inconsistency group |
| `MAX_CSV_SIZE_MB` | `10` | Upload size limit |
| `LOG_LEVEL` | `INFO` | Python logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `LOG_RAW_LLM_RESPONSES` | `false` | Emit raw provider responses at `DEBUG` level when deliberately enabled |
| `CORS_ORIGINS` | `http://localhost:5173,...` | Comma-separated allowed origins |

## Project Structure

```text
Backend/
  app/
    main.py
    models.py
    config.py
    run_store.py
    routers/
      upload.py
      analysis.py
    services/
      csv_service.py
      prompt_service.py
      response_parser.py
      llm_clients.py
      analysis_service.py
      comparison_service.py
  tests/
  requirements.txt
  pyproject.toml
  .env.example
```

## Verification

Run the full local check set after installing dependencies:

```powershell
python -m ruff check .
python -m mypy .
python -m pytest
python -m compileall app tests
```

## Structured Logging

The backend emits structured log lines at two levels:

| Event | Level | When |
|---|---|---|
| Raw LLM response | `DEBUG` | Every provider response when `LOG_RAW_LLM_RESPONSES=true` |
| Parse error | `WARNING` | When a provider response cannot be parsed into the expected JSON shape |

Set both `LOG_LEVEL=DEBUG` and `LOG_RAW_LLM_RESPONSES=true` in `.env` to inspect raw response bodies during debugging. Keep raw response logging disabled for normal development because responses may contain requirement text.

## Notes

- Run state is stored in memory only. Restarting the backend clears all runs.
- The mock LLM path is intentionally deterministic for frontend/backend integration work.
- The live LLM path imports `anthropic` and `openai` only when `USE_REAL_LLM=true`.

## License

This project uses the MIT License. See [LICENSE](LICENSE).
