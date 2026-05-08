# Backend Versioning Guide

This guide explains how backend versions are numbered, documented, restored, and
released.

The current backend version is:

```text
documented version: v1.0.0
stable Git tag:     v1.0.0 once the backend repository is tagged
active baseline:    v1.0.0
```

## Why Versioning Exists

| Goal | Meaning |
|---|---|
| Traceability | Anyone can see what the backend contained at each release |
| Restorability | Any tagged backend version can be restored to a clean working state |
| Readability | A newcomer can understand the backend history without guessing |
| Auditability | Each release explains what changed, why it changed, and how it was tested |

## Three-Tier Backend Version Model

Every version number follows `vX.Y.Z`.

| Tier | Pattern | When to use |
|---|---|---|
| Major baseline | `vX.0.0` | Backend architecture changes significantly, such as adding a database, replacing the run engine, changing the API contract, or introducing a new deployment model |
| Backend feature change | `vX.Y.0` | New backend behavior is added inside the current baseline, such as a new endpoint, improved analysis flow, persistence, logging, export, or frontend contract support |
| Patch | `vX.Y.Z` | A small correction is made, such as a typo, dependency patch, test fix, or configuration tweak |

### Examples

| Version | Tier | What it represents |
|---|---|---|
| `v1.0.0` | Major baseline | First working FastAPI backend with upload, analysis, status, mock LLM, tests, and docs |
| `v1.1.0` | Backend feature change | Example: persistent run history added without changing the core API shape |
| `v1.2.0` | Backend feature change | Example: export endpoints or raw LLM response logging added |
| `v1.2.1` | Patch | Example: a bug fix in CSV parsing or a dependency patch |
| `v2.0.0` | Major baseline | Example: database-backed job queue or breaking API contract change |

The rule is simple: while the backend is based on the version 1 baseline, release normal
work as `v1.1.0`, `v1.2.0`, and so on. Only create `v2.0.0` when a new baseline is
intentionally created.

## Folder Structure

Version documents are stored by major version.

```text
docs/versions/
  index.md
  TEMPLATE.md
  v1/
    v1.0.0.md
    v1.1.0.md
    v1.2.0.md
  v2/
    v2.0.0.md
```

Every released Git tag must have:

| Required item | Example |
|---|---|
| A matching document | `docs/versions/v1/v1.1.0.md` |
| A row in the index | `docs/versions/index.md` |
| A Git tag | `v1.1.0` |
| Verification results | Ruff, mypy, pytest, compileall |

## Core Terms

| Term | Meaning |
|---|---|
| Repository | The folder tracked by Git |
| Commit | A saved snapshot of tracked files |
| Branch | A movable line of work, such as `main` |
| Tag | A fixed named checkpoint, such as `v1.0.0` |
| Frozen baseline | A major-version tag that must never be moved or rewritten |
| Detached HEAD | Viewing a tag directly without being on a branch |
| Clean tree | No uncommitted tracked changes and no untracked files |

## Baseline Freeze Policy

Major baseline tags (`vX.0.0`) are permanent.

| Rule | Detail |
|---|---|
| Never move a baseline tag | Do not amend, retag, or force-push a baseline |
| Never delete a baseline tag | The baseline must always remain restorable |
| Build normal work on top | Use `vX.Y.0` for changes inside the baseline |
| Document before tagging | The version document must exist before the tag is created |

Current frozen baseline:

| Tag | Meaning |
|---|---|
| `v1.0.0` | First intended FastAPI backend baseline |

## Available Version Commands

List released version tags:

```powershell
git tag --list "v*"
```

Show the current tag, commit, and dirty state:

```powershell
git describe --tags --always --dirty
```

Switch to a specific backend version:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\use-version.ps1 -Version v1.0.0
```

Switch, remove ignored generated files, and reinstall dependencies:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\use-version.ps1 -Version v1.0 -CleanIgnored -Install
```

Return to the latest `main` branch:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\use-version.ps1 -Latest -Install
```

Create an editable branch from an old version:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\use-version.ps1 -Version v1.0.0 -Branch work/from-v1.0.0 -Install
```

Preview a switch without changing files:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\use-version.ps1 -Version v1.0 -WhatIf
```

The helper accepts these equivalent formats when the tag exists:

| Input | Resolves to |
|---|---|
| `v1.0.0` | `v1.0.0` |
| `v1.0` | `v1.0.0` |
| `1.0` | `v1.0.0` |
| `1` | `v1.0.0` |

## Version Script Options

The helper script lives at `scripts/use-version.ps1`.

| Option | Meaning |
|---|---|
| `-Version vX.Y.Z` | Switch to a specific version tag |
| `-Latest` | Switch to the latest `main` branch |
| `-Branch name` | Create a new editable branch from the selected version |
| `-Fetch` | Fetch remote branches and tags before switching |
| `-CleanIgnored` | Remove ignored generated files with `git clean -fdX` |
| `-Install` | Run `python -m pip install -r requirements.txt` after switching |
| `-WhatIf` | Show what would happen without making changes |

Use either `-Version` or `-Latest`, not both. The script stops if the working tree has
uncommitted changes to protect source files from being overwritten.

## How To Release A New Backend Version

Follow these steps in order.

### 1. Choose the version number

| Situation | Version to create |
|---|---|
| Major architecture or API baseline change | Increment `X`, set `Y` and `Z` to `0`, such as `v2.0.0` |
| Backend feature change inside the current baseline | Keep `X`, increment `Y`, set `Z` to `0`, such as `v1.1.0` |
| Small correction to an existing release | Keep `X` and `Y`, increment `Z`, such as `v1.0.1` |

### 2. Start from a clean main branch

```powershell
git status
git switch main
git pull origin main
```

### 3. Create a working branch

```powershell
git switch -c feature/v1.1.0
```

### 4. Make the backend or documentation changes

Keep changes scoped to the release.

### 5. Create the version document

Copy the template into the matching major-version folder:

```powershell
Copy-Item docs\versions\TEMPLATE.md docs\versions\v1\v1.1.0.md
```

Fill in every section before tagging.

### 6. Update the version index

Add a new row at the top of `docs/versions/index.md`.

### 7. Update README references

Update `README.md` if setup commands, endpoints, environment variables, or version
references changed.

### 8. Run all checks

All four must pass before release:

```powershell
python -m ruff check .
python -m mypy .
python -m pytest
python -m compileall app tests
```

### 9. Commit

```powershell
git add .
git commit -m "Release v1.1.0"
```

### 10. Merge to main

```powershell
git switch main
git merge --no-ff feature/v1.1.0
```

### 11. Tag the release

```powershell
git tag -a v1.1.0 -m "Backend version 1.1.0"
```

### 12. Push

```powershell
git push origin main
git push origin v1.1.0
```

## Restore Workflows

Restore the current baseline:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\use-version.ps1 -Version v1.0 -CleanIgnored -Install
```

Restore a future version variation:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\use-version.ps1 -Version v1.2 -CleanIgnored -Install
```

Return to latest work:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\use-version.ps1 -Latest -Install
```

Exact reset to GitHub main, destructive:

```powershell
git fetch origin --tags --prune
git switch main
git reset --hard origin/main
git clean -fdX
python -m pip install -r requirements.txt
```

Only use the destructive reset after saving local work.

## Version Document Requirements

Every version document must include these sections:

| Section | What to write |
|---|---|
| Header table | Release date, tag, commit, branch, project version, tier, status |
| Tier classification | Which tier applies and why |
| Plain-language summary | What the version is and what a non-technical reader can do with it |
| What changed | Area, change, and reason |
| What is included | Endpoints, services, tests, documentation, runtime modes |
| What is not included | Missing features and expected future version |
| Required software | Python, pip, Git, PowerShell |
| First-time setup | Clone, install, env, run commands |
| Verify | Ruff, mypy, pytest, compileall results |
| Important files | Key backend files a new developer should read |
| Restore | How to return to the exact version |
| Dependency notes | Package versions and why they exist |
| Frontend assumption | Which frontend/API contract this backend supports |
| Known limitations | What is missing or temporary |
| Upgrade notes | What changes when moving from the previous version |
| Downgrade notes | What changes when returning to the previous version |
| Recommended next work | Numbered list of practical next tasks |
