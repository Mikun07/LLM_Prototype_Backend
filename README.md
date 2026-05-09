# ReqSmell Backend

FastAPI backend for the ReqSmell requirements smell detection prototype.

This backend is the intended service version of the earlier
`genai-requirements-smells` experiment. The script pipeline has been reorganised into
API routes, Pydantic models, services, an in-memory run store, and testable parsing logic.

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
| [Command Reference](docs/COMMANDS.md) | Setup, run, test, and version commands |
| [Versioning Guide](docs/VERSIONING.md) | Backend version policy and release workflow |
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

Important variables in `.env`:

```text
USE_REAL_LLM=false
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
CLAUDE_MODEL=claude-sonnet-4-20250514
OPENAI_MODEL=gpt-4o
LLM_TEMPERATURE=0.1
INCONSISTENCY_MAX_GROUP_SIZE=20
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

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

## Notes

- Run state is stored in memory only. Restarting the backend clears all runs.
- Raw LLM logging paths are reserved in configuration but not yet persisted to disk.
- The mock LLM path is intentionally deterministic for frontend/backend integration work.
- The live LLM path imports `anthropic` and `openai` only when `USE_REAL_LLM=true`.
