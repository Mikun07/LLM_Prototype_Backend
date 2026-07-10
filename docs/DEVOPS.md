# DevOps and Deployment (Backend)

This document defines the environment strategy, build pipeline, configuration management,
logging, and operational approach for the ReqSmell backend. Frontend DevOps is in
`Frontend/docs/DEVOPS.md`.

## Operational Scope

ReqSmell is a local research prototype. The operational requirements are designed
for a single-developer, single-machine environment. A staged or cloud deployment is
not planned for this version.

| Operational requirement | Target |
|---|---|
| Availability | During active research sessions only; downtime between sessions is acceptable |
| Recoverability | Re-run analysis; no persistent data to recover |
| Scalability | Single researcher, small datasets (tens to hundreds of requirements) |
| Automation | Quality checks automated via Python tool commands |
| Observability | Structured stdout logging |

## Environment Strategy

### Development Environment

| Component | Technology | How to start |
|---|---|---|
| Backend | Python + FastAPI + Uvicorn | `python -m uvicorn app.main:app --reload --port 8000` |
| Provider integration | Anthropic SDK, OpenAI SDK | Enabled by `USE_REAL_LLM=true` in `.env` |

The frontend Vite dev proxy forwards `/api/*` requests to `http://localhost:8000`.
Both processes must run in separate terminals; see `Frontend/docs/DEVOPS.md` for
the frontend start command.

### Staging and Production Environments

Not in scope for this version. The prototype is not deployed to any network-accessible
environment.

When a deployment is added in a future version, it should address:

| Area | Consideration |
|---|---|
| HTTPS | TLS termination via reverse proxy (Nginx, Caddy) |
| CORS origins | Restrict `CORS_ORIGINS` to the exact deployed frontend domain |
| Secrets | Use environment variables injected by the hosting platform, not a committed `.env` |
| Process management | Use a process supervisor (systemd, Docker) rather than running uvicorn directly |

## Containerisation

Docker is not used in this version. The backend is developed and run directly on the
host machine using a Python virtual environment.

If containerisation is added in a future version:

| Container | Contents |
|---|---|
| Backend | Python runtime, FastAPI app, `.env` injected as environment variables |
| Frontend | Node build step producing `dist/`; served by Nginx or a static host |

## Build Pipeline

No CI/CD pipeline is configured. All checks run locally before commits.

### Backend Quality Gate

All four commands must pass before committing or releasing:

| Command | What it checks |
|---|---|
| `python -m ruff check .` | Linting and import order |
| `python -m mypy .` | Static type correctness |
| `python -m pytest` | Automated test suite |
| `python -m compileall app tests` | Python file compilability |

If a future CI/CD pipeline is added (such as GitHub Actions), these same commands
should form the pipeline steps.

## Configuration Management

All runtime configuration is managed through environment variables.

| Source | Purpose |
|---|---|
| `.env.example` | Template committed to the repository; contains no real secrets |
| `.env` | Developer copy on the local machine; excluded from version control |
| `app/config.py` | Reads all variables; exposes a typed `Settings` object via `get_settings()` |

No configuration is hardcoded in source files. Defaults in `config.py` allow the
backend to start without a `.env` file in mock mode.

### Secrets Management

| Secret | Where stored | Committed to repository? |
|---|---|---|
| `ANTHROPIC_API_KEY` | `.env` on developer machine | No |
| `OPENAI_API_KEY` | `.env` on developer machine | No |

Provider keys are never passed to the browser. Never use live keys in test fixtures.

## Logging Strategy

Structured log output goes to stdout. The log level is controlled by `LOG_LEVEL` in `.env`.

| Level | When to use |
|---|---|
| `ERROR` | Unrecoverable failures |
| `WARNING` | Recoverable problems, such as parse errors on LLM responses |
| `INFO` | Default level; startup, request handling |
| `DEBUG` | Raw LLM response bodies (opt-in via `LOG_RAW_LLM_RESPONSES=true`) |

Log format:

```text
%(asctime)s %(levelname)s %(name)s %(message)s
```

Example:

```text
2026-07-02 14:33:01,245 WARNING app.services.analysis_service parse_error run=run_abc123 model=claude smell=ambiguity req=REQ-004
```

Structured key=value pairs in log messages make grep-based investigation straightforward.

## Observability

| Signal | Where | How to access |
|---|---|---|
| Backend logs | Stdout of the uvicorn process | Terminal where the backend is running |
| Parse error rate | Backend WARNING logs | Search for `parse_error` in terminal output |
| Raw LLM responses | Backend DEBUG logs | Set `LOG_LEVEL=DEBUG` and `LOG_RAW_LLM_RESPONSES=true` |

No distributed tracing, metrics collection, or dashboarding is in scope for this version.

## Incident Management

| Situation | First action |
|---|---|
| Backend returns 503 for a provider | Check that `USE_REAL_LLM=true` and the correct API key is set in `.env` |
| Pipeline shows `error` status | Check backend terminal output for ERROR or WARNING log lines |
| LLM responses all parse as `parse_error` | Temporarily set `LOG_LEVEL=DEBUG` and `LOG_RAW_LLM_RESPONSES=true`; check if the provider model ID has changed |
| CSV upload rejected with 422 | Confirm the CSV has a column containing requirement text; check COMMANDS.md |
| Results differ significantly between runs | Expected behaviour; LLM outputs are not fully deterministic; document and account for variability in thesis analysis |

## Backup and Recovery

No persistent state exists in this version. All run state is in memory and is lost
when the backend process stops.

| What could be lost | Recovery |
|---|---|
| In-progress analysis run | Re-run the analysis after restarting the backend |
| Configuration | `.env` file is on the researcher's machine; recoverable from `.env.example` template |
| Source code | Version controlled; recoverable from git |

## Version Management

The versioning strategy is defined in `VERSIONING.md`. The three-tier model is:

| Tier | Pattern | What triggers it |
|---|---|---|
| Major baseline | `vX.0.0` | Architecture change, API contract break, major new component |
| Feature change | `vX.Y.0` | New endpoint, analysis behaviour, or significant component |
| Patch | `vX.Y.Z` | Bug fix, dependency update, documentation correction |

Every released version requires a version document, an index entry, and a passing
quality gate before the tag is created.

## Scalability Assessment

This prototype is not designed to scale. The following constraints are intentional
for a thesis prototype and would need to be addressed before any production use:

| Constraint | Impact if scaled | Mitigation needed |
|---|---|---|
| In-memory run store | Lost on restart; no concurrent user isolation | Database-backed store |
| Single-process async | No horizontal scaling | Message queue and worker pool |
| No rate limiting | Could exhaust provider quotas with large parallel usage | Request queuing and rate control |
| No authentication | Any local network access would reach the API | Authentication layer |

## Operational Readiness

| Check | Status |
|---|---|
| Local development environment documented | `../README.md`, COMMANDS.md |
| Quality gates defined and enforced | COMMANDS.md, VERSIONING.md |
| Configuration management defined | This document, `app/config.py`, `.env.example` |
| Logging strategy implemented | `main.py` wires `logging.basicConfig`; `analysis_service.py` emits structured events |
| Secrets excluded from version control | `.gitignore` enforced |
| Known limitations documented | This document, version docs, ARCHITECTURE.md |
| Recovery procedure documented | This document |
