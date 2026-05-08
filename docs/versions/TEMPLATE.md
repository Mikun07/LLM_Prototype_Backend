# vX.Y.Z - Release Title

| Field | Value |
|---|---|
| Release date | YYYY-MM-DD |
| Git tag | `vX.Y.Z` |
| Tagged commit | `commit-sha` |
| Branch at release | `main` |
| Project version | `X.Y.Z` |
| Tier | Major baseline / Backend feature change / Patch |
| Status | Draft / Stable / Deprecated |

## Tier Classification

Pick exactly one row and mark it.

| Tier | Pattern | This version |
|---|---|---|
| Major baseline | `vX.0.0` - backend architecture, API contract, or deployment baseline changes significantly | |
| Backend feature change | `vX.Y.0` - endpoint, service, workflow, persistence, logging, or analysis behavior added inside the baseline | |
| Patch | `vX.Y.Z` - small bug fix, dependency patch, typo, or config tweak | |

State the tier and what qualifies this version for it in one or two sentences below the table.

## Plain-Language Summary

Explain what this backend version is, why it exists, and what a non-technical reader can
do with it. Keep this to 3-5 sentences.

## What Changed From The Previous Version

| Area | What changed | Why |
|---|---|---|
| | | |

## Who This Version Is For

| Person | What they can do with this version |
|---|---|
| New developer | |
| Researcher | |
| Maintainer | |
| Reviewer | |

## What Is Included

| Area | Details |
|---|---|
| API routes | |
| Services | |
| Runtime modes | |
| Tests | |
| Documentation | |

## What Is Not Included Yet

| Missing feature | Expected in which future version |
|---|---|
| | |

## Required Software

| Software | Recommended version | Check command |
|---|---|---|
| Python | 3.11 or later | `python --version` |
| pip | Bundled with Python | `python -m pip --version` |
| Git | Current stable | `git --version` |
| PowerShell | 5.1 or later | `$PSVersionTable.PSVersion` |

## First-Time Setup

```powershell
git clone <backend-repository-url>
cd Backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -m uvicorn app.main:app --reload --port 8000
```

Open in your browser:

```text
http://127.0.0.1:8000/docs
```

## Verify This Version

Run all four checks. All must pass before this version can be tagged.

```powershell
python -m ruff check .
python -m mypy .
python -m pytest
python -m compileall app tests
```

Expected results:

| Command | Expected result |
|---|---|
| `python -m ruff check .` | 0 errors |
| `python -m mypy .` | 0 errors |
| `python -m pytest` | All tests pass |
| `python -m compileall app tests` | Compilation succeeds |

## Important Files

| File | Purpose |
|---|---|
| `app/main.py` | FastAPI application and router registration |
| `app/models.py` | Pydantic API contracts shared with the frontend |
| `app/routers/upload.py` | CSV upload endpoint |
| `app/routers/analysis.py` | Analysis start and status endpoints |
| `app/services/csv_service.py` | CSV validation and parsing |
| `app/services/analysis_service.py` | Background run orchestration |
| `app/services/llm_clients.py` | Mock and live LLM clients |
| `tests/` | Backend test suite |

## Backend Commands

| Command | Purpose |
|---|---|
| `python -m uvicorn app.main:app --reload --port 8000` | Start backend dev server |
| `python -m ruff check .` | Run lint checks |
| `python -m mypy .` | Run type checks |
| `python -m pytest` | Run tests |
| `python -m compileall app tests` | Compile Python source files |
| `powershell -ExecutionPolicy Bypass -File .\scripts\use-version.ps1` | Switch versions |

## Restore This Version

View the exact tagged snapshot without changing your branch:

```powershell
git fetch --tags
git switch --detach vX.Y.Z
python -m pip install -r requirements.txt
```

Restore this version and remove generated files:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\use-version.ps1 -Version vX.Y.Z -CleanIgnored -Install
```

Create an editable branch from this version:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\use-version.ps1 -Version vX.Y.Z -Branch work/from-vX.Y.Z -Install
```

Return to latest `main`:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\use-version.ps1 -Latest -Install
```

## Dependency Notes

| Package | Version | Reason included or changed |
|---|---|---|
| | | |

## Frontend Assumption

State which frontend version or API contract this backend supports. Include the expected
frontend URL and backend URL if relevant.

## Known Limitations

| Limitation | Impact |
|---|---|
| | |

## Upgrade Notes

What should a developer know when moving from the previous version to this one? List any
breaking endpoint changes, renamed environment variables, dependency changes, or data
migration steps.

## Downgrade Notes

What should a developer know before returning to the previous version? List anything that
would break or be missing after downgrading.

## Recommended Next Work

1. First clear next task.
2. Second clear next task.
3. Any documentation or test updates needed.
