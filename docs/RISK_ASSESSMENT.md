# Risk Assessment (Backend)

This document identifies risks to the backend of the ReqSmell prototype and the
mitigation strategy for each. Frontend risks are in `Frontend/docs/RISK_ASSESSMENT.md`.

Probability and impact are rated: Very Low / Low / Medium / High / Very High.
Classification combines the two: Critical / High / Medium / Low.

## Technical Risks

### RT-001: LLM Provider API Unavailability

| Field | Detail |
|---|---|
| Description | Anthropic or OpenAI experiences an outage or rate-limits the account during a research session |
| Probability | Low |
| Impact | High |
| Classification | Medium |
| Mitigation | Retry logic with configurable attempts (`LLM_MAX_RETRIES`); mock mode allows full testing without providers; pipelines isolate per model, so one provider failing does not stop the other |
| Residual risk | An extended outage during a time-critical research session would delay results |

### RT-002: LLM Response Format Drift

| Field | Detail |
|---|---|
| Description | A provider updates its model behaviour and returns responses in a format the parser does not handle |
| Probability | Medium |
| Impact | Medium |
| Classification | Medium |
| Mitigation | Parser has three fallback paths (JSON, legacy yes/no, parse error); unknown values are normalised to safe defaults rather than causing crashes; parse errors are logged as warnings |
| Residual risk | Silent degradation: more results classified as SMELL due to parse errors being treated as ambiguous |

### RT-003: In-Memory Run Store Loss

| Field | Detail |
|---|---|
| Description | The backend process restarts during analysis, losing all run state |
| Probability | Low |
| Impact | High |
| Classification | Medium |
| Mitigation | Researcher must not restart the backend during an active run; runs are short for typical thesis dataset sizes |
| Residual risk | Loss of in-progress results if the process crashes; acceptable for a thesis prototype where re-runs are feasible |

### RT-004: CSV Column Detection Failure

| Field | Detail |
|---|---|
| Description | An uploaded CSV uses non-standard column names and the detector misses them |
| Probability | Medium |
| Impact | Medium |
| Classification | Medium |
| Mitigation | Column detector uses alias matching across common naming conventions; detected columns are shown in the UI for review before analysis starts; documentation describes the expected column names |
| Residual risk | User may need to rename columns in their CSV before uploading |

### RT-005: Concurrent Pipeline Race Condition

| Field | Detail |
|---|---|
| Description | Multiple async pipeline tasks write to the run store at the same time and corrupt progress state |
| Probability | Low |
| Impact | Medium |
| Classification | Low |
| Mitigation | Each pipeline writes only to its own key in the run store; asyncio single-threaded event loop serialises writes naturally |
| Residual risk | Negligible under normal operation |

### RT-006: Type Contract Mismatch Between Backend and Frontend

| Field | Detail |
|---|---|
| Description | A field is added or changed in `app/models.py` without updating `Frontend/src/types/index.ts`, causing silent data loss or runtime errors |
| Probability | Medium |
| Impact | High |
| Classification | High |
| Mitigation | Both files are documented as a shared contract; architecture document explicitly cross-references them; TypeScript strict mode catches unexpected `undefined` fields at compile time |
| Residual risk | Manual synchronisation is still required; no automated contract test exists between the two files |

## Security Risks

### RS-001: API Key Exposure

| Field | Detail |
|---|---|
| Description | Provider API keys are committed to the repository or exposed in backend logs |
| Probability | Low |
| Impact | Very High |
| Classification | High |
| Mitigation | `.env` is in `.gitignore`; `.env.example` contains no real keys; all provider calls are server-side; logging writes raw LLM responses, not key values |
| Residual risk | Negligible if the `.gitignore` is respected |

### RS-002: Malicious CSV Upload

| Field | Detail |
|---|---|
| Description | A crafted CSV file causes unexpected backend behaviour, such as processing an unexpectedly large payload or injecting content into LLM prompts |
| Probability | Low |
| Impact | Medium |
| Classification | Low |
| Mitigation | File size is limited by `MAX_CSV_SIZE_MB`; CSV rows are parsed through a controlled schema; requirement text is injected into prompts with explicit field boundaries in the JSON schema |
| Residual risk | Prompt injection via requirement text content is theoretically possible; mitigated by the structured JSON response format |

### RS-003: CORS Misconfiguration

| Field | Detail |
|---|---|
| Description | The backend CORS policy is too permissive, allowing arbitrary origins to call the API |
| Probability | Low |
| Impact | Medium |
| Classification | Low |
| Mitigation | `CORS_ORIGINS` defaults to `localhost:5173` only; any future deployment must restrict this explicitly |
| Residual risk | Acceptable for a local thesis prototype; would need hardening before any network-exposed deployment |

### RS-004: Python Dependency Vulnerability

| Field | Detail |
|---|---|
| Description | A package in `requirements.txt` contains a known security vulnerability |
| Probability | Medium |
| Impact | Medium |
| Classification | Medium |
| Mitigation | Dependencies are pinned to specific versions; can be audited with `pip-audit`; versions are reviewed when updating |
| Residual risk | Vulnerabilities published after the last audit would not be caught until the next check |

## Operational Risks

### RO-001: Development Environment Inconsistency

| Field | Detail |
|---|---|
| Description | The backend behaves differently on different machines due to Python version differences or virtual environment issues |
| Probability | Medium |
| Impact | Medium |
| Classification | Medium |
| Mitigation | Minimum Python version is documented in SETUP.md; dependencies are pinned in `requirements.txt` |
| Residual risk | Platform-specific issues (Windows path separators, OneDrive sync delays) may still occur |

### RO-003: Log Verbosity

| Field | Detail |
|---|---|
| Description | `LOG_LEVEL=DEBUG` with `LOG_RAW_LLM_RESPONSES=true` produces large log volumes containing full requirement text |
| Probability | Low |
| Impact | Low |
| Classification | Low |
| Mitigation | Default `LOG_LEVEL=INFO` suppresses debug output; researcher must explicitly enable debug logging |
| Residual risk | Negligible; no production deployment is planned |

## Project Risks

### RP-001: LLM Result Non-Determinism

| Field | Detail |
|---|---|
| Description | LLM outputs vary between runs even for identical inputs, making results difficult to reproduce exactly |
| Probability | High |
| Impact | Medium |
| Classification | High |
| Mitigation | Temperature is configurable and documented (`LLM_TEMPERATURE=0.1` default); prompt version is embedded in every prompt message for traceability; thesis analysis should acknowledge and account for variability |
| Residual risk | Some result variation between runs is expected and must be discussed in the thesis |

### RP-002: Scope Creep

| Field | Detail |
|---|---|
| Description | Feature additions extend the prototype beyond the thesis scope, consuming time without improving research outcomes |
| Probability | Medium |
| Impact | Medium |
| Classification | Medium |
| Mitigation | Scope boundaries are defined in REQUIREMENTS.md; versioning governance requires each release to justify its tier classification and link changes to requirements |
| Residual risk | Manageable with discipline |

### RP-003: Provider Cost Overrun

| Field | Detail |
|---|---|
| Description | Running large datasets through live LLM providers incurs unexpected API costs |
| Probability | Low |
| Impact | Medium |
| Classification | Low |
| Mitigation | Mock mode is the default and free; `INCONSISTENCY_MAX_GROUP_SIZE` limits tokens per call; researcher should estimate token usage before large live runs |
| Residual risk | Manageable with monitoring of provider dashboards |

## Risk Matrix

| Risk | Probability | Impact | Classification |
|---|---|---|---|
| RT-006: Type contract mismatch | Medium | High | High |
| RS-001: API key exposure | Low | Very High | High |
| RP-001: LLM non-determinism | High | Medium | High |
| RT-002: LLM response format drift | Medium | Medium | Medium |
| RT-003: In-memory run store loss | Low | High | Medium |
| RT-004: CSV column detection failure | Medium | Medium | Medium |
| RS-004: Python dependency vulnerability | Medium | Medium | Medium |
| RO-001: Development environment inconsistency | Medium | Medium | Medium |
| RP-002: Scope creep | Medium | Medium | Medium |
| RT-001: Provider API unavailability | Low | High | Medium |
| RT-005: Concurrent pipeline race condition | Low | Medium | Low |
| RS-002: Malicious CSV upload | Low | Medium | Low |
| RS-003: CORS misconfiguration | Low | Medium | Low |
| RO-003: Log verbosity | Low | Low | Low |
| RP-003: Provider cost overrun | Low | Medium | Low |

## Accepted Risks

| Risk | Reason accepted |
|---|---|
| RT-003: In-memory run store loss | Re-running is feasible at thesis dataset sizes |
| RS-003: CORS misconfiguration | No network-exposed deployment is planned |
| RP-003: Provider cost overrun | Researcher controls when live mode is used |
