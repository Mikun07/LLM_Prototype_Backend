# Requirements Engineering (Backend)

This document defines the system-level requirements for the ReqSmell prototype and
identifies which are implemented in the backend. Frontend requirements are in
`Frontend/docs/REQUIREMENTS.md`.

## Problem Statement

Software requirement specifications contain defects that are difficult to detect manually
at scale. Two categories of defect are particularly common:

| Defect | Description |
|---|---|
| Ambiguity | A requirement can be interpreted in more than one way, leaving implementation teams without a clear, single meaning |
| Inconsistency | Two or more requirements contradict or conflict with each other, making it impossible to satisfy all of them simultaneously |

These defects increase the cost of software projects by delaying design decisions,
causing rework, and producing systems that do not match what stakeholders actually needed.

The question this prototype investigates is:

> Can large language models detect ambiguity and inconsistency in software requirements
> specifications with sufficient accuracy to be useful in practice, and do different LLMs
> produce consistent results with each other?

## Stakeholders

| Stakeholder | Role | Concern |
|---|---|---|
| Researcher | Thesis author | Evaluate LLM detection accuracy and inter-model agreement |
| Supervisor | Academic reviewer | Rigor, reproducibility, and defensibility of results |
| Requirements engineer | Potential future user | Tool usability and output quality |
| Developer | Prototype maintainer | Code maintainability, testability, and documentation |
| LLM providers | Anthropic, OpenAI | API usage within rate limits and terms of service |

## Scope

| In scope | Out of scope |
|---|---|
| CSV upload and parsing | Persistent database storage |
| Ambiguity detection via LLM | Authentication and user accounts |
| Inconsistency detection via LLM | Multi-user access |
| Side-by-side model comparison | Deployment to a public environment |
| Per-requirement classification and explanation | Integration with issue trackers or project tools |
| Export of results to CSV and PDF | Version history of requirement sets |

## User Personas

### Persona 1: Researcher Using the Tool for Thesis Evaluation

| Field | Detail |
|---|---|
| Background | Postgraduate student in software engineering |
| Goal | Upload a real or synthetic requirements dataset, run both models, and compare their outputs |
| Technical proficiency | Comfortable with command-line tools and local server setup |
| Success criteria | Tool produces per-requirement smell classifications with explanations and a comparison summary |

### Persona 2: Developer Maintaining or Extending the Prototype

| Field | Detail |
|---|---|
| Background | Software developer familiar with Python and TypeScript |
| Goal | Understand the codebase, run the test suite, and safely make changes |
| Technical proficiency | High |
| Success criteria | Can set up, run, test, and extend the system using only the documentation |

### Persona 3: Academic Reviewer Evaluating the Work

| Field | Detail |
|---|---|
| Background | Academic with software engineering domain knowledge |
| Goal | Assess the rigor, design, and results of the research |
| Technical proficiency | Moderate |
| Success criteria | Can read the documentation and understand what was built, why, and what the results mean |

## User Stories

### Core

| ID | Story |
|---|---|
| US-001 | As a researcher, I want to upload a CSV file of requirements so that the system can analyse them |
| US-002 | As a researcher, I want to select which models and smell types to run so that I can control the analysis scope |
| US-003 | As a researcher, I want to see real-time progress during analysis so that I know the system is working |
| US-004 | As a researcher, I want to see per-requirement smell classifications so that I can assess LLM detection accuracy |
| US-005 | As a researcher, I want to compare Claude and ChatGPT results side by side so that I can evaluate inter-model agreement |
| US-006 | As a researcher, I want to export results to CSV so that I can use them in further analysis |
| US-007 | As a researcher, I want to export results to PDF so that I can include them in the thesis submission |

### Configuration

| ID | Story |
|---|---|
| US-008 | As a researcher, I want to set the LLM temperature so that I can control output determinism |
| US-009 | As a researcher, I want to set the maximum group size for inconsistency analysis so that I can manage token costs |

### Developer

| ID | Story |
|---|---|
| US-010 | As a developer, I want to run the system without real API keys so that I can develop and test without cost |
| US-011 | As a developer, I want structured log output so that I can diagnose parsing and provider errors |

## Functional Requirements

All functional requirements are implemented in the backend API. The frontend drives them
through the UI but the logic lives here.

| ID | Requirement | Implemented in |
|---|---|---|
| FR-001 | The system shall accept a CSV file upload and extract requirement rows from it | `routers/upload.py`, `csv_service.py` |
| FR-002 | The system shall detect the column names for requirement ID, text, domain, type, and project from the uploaded file | `csv_service.py` |
| FR-003 | The system shall reject CSV files that do not contain a text column | `csv_service.py` |
| FR-004 | The system shall reject CSV files that exceed the configured size limit | `routers/upload.py` |
| FR-005 | The system shall allow the user to select one or both LLM providers (Claude, ChatGPT) | `analysis_service.py`, `models.py` |
| FR-006 | The system shall allow the user to select one or both smell types (ambiguity, inconsistency) | `analysis_service.py`, `models.py` |
| FR-007 | The system shall classify each requirement as ambiguous or not ambiguous with a confidence level and explanation | `response_parser.py`, `prompt_service.py` |
| FR-008 | The system shall classify each requirement as having an ambiguity type (lexical, syntactic, referential, semantic, or none) | `response_parser.py` |
| FR-009 | The system shall detect inconsistencies between pairs of requirements within the same domain and project group | `analysis_service.py`, `prompt_service.py` |
| FR-010 | The system shall run selected model and smell type combinations concurrently | `analysis_service.py` async pipelines |
| FR-011 | The system shall report progress for each pipeline independently | `run_store.py`, `routers/status.py` |
| FR-012 | The system shall continue other pipelines if one pipeline fails | `analysis_service.py` exception handling |
| FR-013 | The system shall produce a per-model report summarising smell counts, rates, and breakdowns by domain and type | `routers/status.py` response model |
| FR-014 | The system shall produce a comparison report showing where Claude and ChatGPT agree and disagree | `comparison_service.py` |
| FR-015 | The system shall allow result tables to be exported as CSV files | Frontend; backend provides the data |
| FR-016 | The system shall allow reports to be exported as PDF files | Frontend; backend provides the data |
| FR-017 | The system shall operate in mock mode without requiring real provider API keys | `llm_clients.py` mock mode, `USE_REAL_LLM` flag |

## Non-Functional Requirements (Backend)

### Performance

| ID | Requirement |
|---|---|
| NFR-001 | The upload endpoint shall respond within 5 seconds for files up to the configured size limit |
| NFR-003 | The system shall not block the main process during LLM calls |

### Reliability

| ID | Requirement |
|---|---|
| NFR-004 | A transient provider error shall be retried up to the configured maximum before the pipeline is marked as failed |
| NFR-005 | A parse error on an LLM response shall produce a recorded result rather than a crash |
| NFR-006 | A failed pipeline shall not prevent other pipelines from completing |

### Maintainability

| ID | Requirement |
|---|---|
| NFR-007 | The backend shall pass ruff, mypy, and pytest checks before any release |
| NFR-009 | All API contracts shall be defined in `app/models.py` and kept in sync with `Frontend/src/types/index.ts` |

### Security

| ID | Requirement |
|---|---|
| NFR-010 | Provider API keys shall not be stored in browser code or transmitted to the client |
| NFR-011 | The backend shall validate and sanitise CSV input before processing |
| NFR-012 | CORS origins shall be explicitly configured and not open by default |

## Requirements Prioritisation

| Priority | Requirements |
|---|---|
| Must have | FR-001 to FR-017, NFR-004, NFR-005, NFR-006, NFR-010 |
| Should have | NFR-001, NFR-003, NFR-007, NFR-009 |
| Could have | Saved run history, database-backed run store |
| Will not have (this version) | Authentication, multi-user support, public deployment, database persistence |

## Acceptance Criteria

| Requirement | Acceptance Criteria |
|---|---|
| FR-001 | Given a valid CSV file, when it is uploaded, then the system returns a list of parsed requirement rows |
| FR-003 | Given a CSV with no text column, when it is uploaded, then the system returns a 422 response with a plain-language error |
| FR-004 | Given a CSV larger than the configured limit, when it is uploaded, then the system returns a 413 response |
| FR-007 | Given a requirement row, when analysed, then the result contains a label (SMELL or CLEAN), confidence (HIGH, MEDIUM, or LOW), and an explanation |
| FR-008 | Given an ambiguous requirement, when analysed, then the result contains an ambiguity type that is one of lexical, syntactic, referential, or semantic |
| FR-010 | Given two models and two smell types selected, when analysis starts, then four pipelines run and report progress independently |
| FR-012 | Given one pipeline raises an unrecoverable error, when analysis runs, then the other pipelines complete and report their results |
| FR-014 | Given both Claude and ChatGPT reports are available, when the comparison is built, then it shows agreement status for each requirement pair |
| FR-017 | Given `USE_REAL_LLM=false`, when analysis runs, then no network calls are made to Anthropic or OpenAI |
| NFR-010 | Given any frontend network response, when inspected, then no API key is present in the response body or headers |

## Traceability Summary

| Stakeholder need | User story | Functional requirement | Covered by |
|---|---|---|---|
| Detect ambiguity | US-001, US-004 | FR-001, FR-007, FR-008 | `analysis_service.py`, `response_parser.py`, `prompt_service.py` |
| Detect inconsistency | US-001, US-004 | FR-001, FR-009 | `analysis_service.py`, `response_parser.py`, `prompt_service.py` |
| Compare models | US-005 | FR-014 | `comparison_service.py` |
| Development without API keys | US-010 | FR-017 | `llm_clients.py` mock mode |
| Diagnose errors | US-011 | NFR-005 | `analysis_service.py` logging, `response_parser.py` fallback paths |
