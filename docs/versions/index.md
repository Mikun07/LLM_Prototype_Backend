# Backend Version Index

Every released backend version has a document in the matching major-version folder.

```text
docs/versions/
  v1/
  v2/
  index.md
  TEMPLATE.md
```

## Version History

| Version | Date | Tier | Summary |
|---|---|---|---|
| [v1.0.0](v1/v1.0.0.md) | 2026-05-08 | Major baseline | First working FastAPI backend for upload, analysis, status polling, mock LLM, and tests |

## Three-Tier Version Model

| Tier | Pattern | Meaning | Example |
|---|---|---|---|
| Major baseline | `vX.0.0` | Backend architecture or API baseline changes significantly | `v1.0.0`, `v2.0.0` |
| Backend feature change | `vX.Y.0` | New backend behavior inside the current baseline | `v1.1.0`, `v1.2.0` |
| Patch | `vX.Y.Z` | Small correction, dependency patch, typo, or config tweak | `v1.0.1` |

## Rules

- Every released Git tag must have a matching document before the tag is created.
- Major baseline tags (`vX.0.0`) are frozen and must never be moved or rewritten.
- Normal work based on `v1.0.0` becomes `v1.1.0`, `v1.2.0`, and so on.
- Patches (`vX.Y.Z`) are only used for corrections to an existing release.
- New major folders (`v2/`, `v3/`) are created only when a new `vX.0.0` baseline is released.

## Current State

Current version: `v1.0.0`

Active major baseline: `v1.0.0`

Next expected release: `v1.1.0` for backend feature work or `v1.0.1` for a patch.
