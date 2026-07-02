# Security Engineering (Backend)

This document defines the security design for the backend of the ReqSmell prototype.
Frontend security considerations are in `Frontend/docs/SECURITY.md`.

## Scope

The backend is the only component that holds secrets (provider API keys), calls external
APIs, handles file uploads, and persists run state. The security posture for this
version focuses on preventing accidental key exposure and protecting the API boundary
during local use.

Production-grade concerns such as authentication, session management, and infrastructure
security are noted but out of scope for this version.

## Asset Identification

| Asset | Sensitivity | Location |
|---|---|---|
| Anthropic API key | High | `.env` file on the server machine; never in source control or browser |
| OpenAI API key | High | `.env` file on the server machine; never in source control or browser |
| Uploaded requirement text | Medium | In-memory during analysis; not persisted to disk |
| LLM responses | Medium | In-memory during analysis; logged at DEBUG level only when enabled |
| Analysis results | Medium | In-memory run store; cleared on process restart |
| Backend source code | Low | Local file system; version controlled without secrets |

## Threat Model (STRIDE)

### Spoofing

| Threat | Applies? | Control |
|---|---|---|
| Impersonation of a legitimate user | No | No authentication in this version; single-user local deployment assumed |
| Impersonation of a provider endpoint | Unlikely | Anthropic and OpenAI SDKs use HTTPS with certificate validation by default |

### Tampering

| Threat | Applies? | Control |
|---|---|---|
| Modification of requirement text in transit | Low risk | All communication is local (localhost); no network transit |
| Modification of CSV before upload | Researcher's own file | Out of scope |
| Prompt injection via requirement text | Possible | Requirement text is injected into a structured JSON schema prompt with explicit field boundaries; JSON response format separates LLM reasoning from input |

### Repudiation

| Threat | Applies? | Control |
|---|---|---|
| Denying that a run was performed | Not a concern | Single-user prototype; no audit requirement |

### Information Disclosure

| Threat | Applies? | Control |
|---|---|---|
| API keys exposed in source control | Mitigated | `.env` is in `.gitignore`; `.env.example` contains no real keys |
| API keys exposed in browser traffic | Mitigated | All provider calls are server-side; the browser never receives keys |
| API keys exposed in logs | Mitigated | Logging writes raw LLM responses, not environment variables; key fields are not logged |
| Requirement text exposed to third parties | Accepted | Live mode sends requirement text to Anthropic/OpenAI APIs; researcher must be aware of this when using sensitive requirements |

### Denial of Service

| Threat | Applies? | Control |
|---|---|---|
| Large CSV file exhausting memory | Mitigated | `MAX_CSV_SIZE_MB` enforced at upload; 413 returned for oversized files |
| Excessive polling exhausting backend resources | Low risk | Polling is 1 200 ms from a single browser tab; rate limiting not needed at this scale |
| Provider rate limiting causing pipeline failure | Mitigated | Retry logic with backoff; billing errors are non-retried and reported clearly |

### Elevation of Privilege

| Threat | Applies? | Control |
|---|---|---|
| Accessing admin or system resources via the API | Not applicable | No privileged operations exist in the API; single-user prototype |

## Attack Surface

| Surface | Risk | Control |
|---|---|---|
| `POST /api/upload` | Malicious or oversized file upload | Size limit, content-type check, CSV-only parsing |
| `POST /api/analyse` | Malformed JSON request body | Pydantic validation rejects invalid shapes with 422 |
| `GET /api/status/{run_id}` | Enumeration of run IDs | Low risk in local deployment; returns 404 for unknown IDs |
| Environment file (`.env`) | Key exposure via accidental commit | `.gitignore` enforced; `.env.example` is the only committed template |
| LLM prompt construction | Prompt injection via requirement text | Structured JSON schema prompt format; requirement text is a labelled field, not a free-form instruction |
| Python dependencies | Known vulnerability in a package | Dependencies pinned to specific versions; can be audited with `pip-audit` |

## Data Protection

| Data | At Rest | In Transit |
|---|---|---|
| API keys | Stored only in `.env` on the local machine | Never transmitted to the browser |
| Requirement text | Held in memory only during the request lifecycle | Sent to provider APIs over HTTPS (live mode only) |
| Analysis results | Held in memory only; cleared on restart | Returned to browser over localhost HTTP |
| Log output | Written to stdout only when logging is enabled | Not transmitted externally |

## Secure Coding Requirements

### Input Validation

| Rule | Where enforced |
|---|---|
| File size must not exceed `MAX_CSV_SIZE_MB` | `routers/upload.py` before parsing |
| Uploaded file must be parseable as UTF-8 CSV | `csv_service.py` |
| Request bodies must match Pydantic model schemas | FastAPI validation layer |
| LLM response values must match valid enumerations | `normalise_confidence()`, `normalise_ambiguity_type()` in `response_parser.py` |

### Output Encoding

| Rule | Where enforced |
|---|---|
| API responses are serialised JSON only | FastAPI and Pydantic handle serialisation |
| No HTML output rendered from user-supplied content | No server-side rendering; frontend handles display |

### Error Handling

| Rule | Where enforced |
|---|---|
| Parse errors produce a recorded fallback result, not a 500 | `parse_ambiguity_response()`, `parse_inconsistency_response()` fallback paths |
| Provider errors produce a pipeline `error` status, not a crash | `_run_pipeline()` exception catch in `analysis_service.py` |
| Internal error details are not exposed to the client in 5xx responses | FastAPI default error handler |

### Dependency Security

| Rule | Frequency |
|---|---|
| Python dependencies are pinned in `requirements.txt` | Enforced by explicit version pins |
| Provider SDKs must be kept up to date when security patches are released | Manual review when updating |

## Security Monitoring

| Event | Level | Where logged |
|---|---|---|
| Parse error on LLM response | `WARNING` | `app.services.analysis_service` logger |
| Raw LLM response body | `DEBUG` (opt-in) | `app.services.analysis_service` logger |

No alerting or centralised log collection is in scope for this prototype. All logging
goes to stdout and is visible in the terminal where the backend is running.

## Security Readiness Review

| Check | Status |
|---|---|
| API keys not in source control | Enforced via `.gitignore` and `.env.example` |
| API keys not transmitted to browser | Provider calls are server-side only |
| File upload size limited | `MAX_CSV_SIZE_MB` enforced |
| Input validation on all endpoints | Pydantic models and CSV service |
| LLM response values normalised to safe enumerations | `normalise_confidence()`, `normalise_ambiguity_type()` |
| Parse errors produce fallback results, not crashes | Verified by test suite |
| CORS origins restricted to localhost | `CORS_ORIGINS` configuration |
| No hardcoded secrets in source | Verified by review |

## Out of Scope for This Version

| Security concern | Reason excluded |
|---|---|
| Authentication and session management | Single-user local prototype |
| Authorisation and role-based access control | No multi-user access |
| HTTPS for local development | Localhost only; HTTPS adds no meaningful protection |
| Penetration testing | Thesis prototype scope |
| Audit trails and compliance logging | Not required for academic research |
| Secrets management service | `.env` on a local machine is sufficient for this scope |
