# Backend Command Reference

This document explains every backend command in plain language.

## Daily Development Commands

| Command | What it does | When to use it |
|---|---|---|
| `python -m venv .venv` | Creates a local Python virtual environment | First setup |
| `.\.venv\Scripts\Activate.ps1` | Activates the virtual environment in PowerShell | Before installing or running the backend |
| `python -m pip install -r requirements.txt` | Installs backend dependencies | First setup, after switching versions, after dependency changes |
| `Copy-Item .env.example .env` | Creates local environment settings | First setup |
| `python -m uvicorn app.main:app --reload --port 8000` | Starts the FastAPI dev server | While developing or testing with the frontend |

## API Commands

| Command | What it checks |
|---|---|
| `Invoke-RestMethod http://127.0.0.1:8000/health` | Confirms the backend is running |
| Open `http://127.0.0.1:8000/docs` | Opens the interactive FastAPI documentation |
| Open `http://127.0.0.1:8000/openapi.json` | Shows the raw OpenAPI schema |

## Quality Commands

| Command | What it checks | Should pass before commit? |
|---|---|---|
| `python -m ruff check .` | Python linting, import order, and policy checks | Yes |
| `python -m mypy .` | Static typing across the backend | Yes |
| `python -m pytest` | Automated backend tests | Yes |
| `python -m compileall app tests` | Confirms Python files compile | Yes |

## Version Commands

Version `v1.0.0` is the first frozen backend baseline. Ordinary backend work based on
this baseline should be released as `v1.1.0`, `v1.2.0`, and so on until a new major
baseline such as `v2.0.0` is intentionally created.

| Command | What it does |
|---|---|
| `git tag --list "v*"` | Lists available Git version tags |
| `git describe --tags --always --dirty` | Shows the current tag or commit |
| `powershell -ExecutionPolicy Bypass -File .\scripts\use-version.ps1 -Version v1.0.0` | Switches to the exact version-1 baseline |
| `powershell -ExecutionPolicy Bypass -File .\scripts\use-version.ps1 -Version v1.0 -Install` | Switches to `v1.0.0` and installs Python dependencies |
| `powershell -ExecutionPolicy Bypass -File .\scripts\use-version.ps1 -Version 1.0 -CleanIgnored -Install` | Restores a clean baseline and dependencies |
| `powershell -ExecutionPolicy Bypass -File .\scripts\use-version.ps1 -Version v1.2 -CleanIgnored -Install` | Restores a future version-1 variation when that tag exists |
| `powershell -ExecutionPolicy Bypass -File .\scripts\use-version.ps1 -Latest -Install` | Switches back to `main` and installs dependencies |
| `powershell -ExecutionPolicy Bypass -File .\scripts\use-version.ps1 -Version v1.0 -Branch work/from-v1.0.0` | Creates an editable branch from a version tag |

The version helper accepts exact tags and shorthand. For example, `v1.0.0`, `v1.0`,
`1.0`, and `1` all resolve to `v1.0.0` when that tag exists.

## Git Commands

| Command | Meaning |
|---|---|
| `git status` | Shows changed, staged, and untracked files |
| `git log --oneline --decorate -5` | Shows recent commits and tags |
| `git fetch origin --tags --prune` | Updates remote branches and version tags |
| `git switch main` | Moves to the main branch |
| `git switch --detach v1.0.0` | Views the baseline exactly as tagged |
| `git switch -c work/from-v1.0.0 v1.0.0` | Creates an editable branch from the baseline |
| `git tag --list "v*"` | Lists version tags |
| `git tag -a v1.0.0 -m "Backend version 1.0.0"` | Creates an annotated baseline tag |
| `git push origin main` | Pushes the main branch to GitHub |
| `git push origin v1.0.0` | Pushes the version tag to GitHub |

## Script Details

The version helper runs directly with PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\use-version.ps1
```

| Option | Required? | Meaning |
|---|---|---|
| `-Version vX.Y.Z` | Required unless `-Latest` is used | Switch to a specific Git tag |
| `-Latest` | Required unless `-Version` is used | Switch to `main` |
| `-Branch branch-name` | Optional | Create a branch from the selected version |
| `-Fetch` | Optional | Fetch latest tags and remote state first |
| `-CleanIgnored` | Optional | Remove ignored generated files with `git clean -fdX` |
| `-Install` | Optional | Run `python -m pip install -r requirements.txt` after switching |
| `-WhatIf` | Optional | Show what would happen without changing files |

The script refuses to switch versions if the working tree has uncommitted tracked or
untracked changes. This protects your work.

## Recommended Command Order

For first setup:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -m ruff check .
python -m mypy .
python -m pytest
python -m compileall app tests
python -m uvicorn app.main:app --reload --port 8000
```

For normal development:

```powershell
git status
python -m uvicorn app.main:app --reload --port 8000
python -m ruff check .
python -m mypy .
python -m pytest
```

For a clean version restore:

```powershell
git status
powershell -ExecutionPolicy Bypass -File .\scripts\use-version.ps1 -Version v1.0 -CleanIgnored -Install
```

For returning to latest work:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\use-version.ps1 -Latest -Install
```
