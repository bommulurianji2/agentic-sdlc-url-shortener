# Requirements Baseline — Agentic SDLC URL Shortener

**Status:** DRAFT v3 — awaiting Human Gate 1 (Requirement Approval)
**Revision history:**
- v1 → v2: added explicit, traceable requirements for the agentic orchestration, governance, traceability, metrics, replanning, and submission-deliverable expectations (v1 only had the application-level requirements).
- v2 → v3: reviewer asked for a second, line-by-line verification against the original 12-item list. Found and fixed two real gaps: (1) the brownfield scenario only demonstrated "enhancement," not the "enhancements, refactoring, or bug fixes" the original item names — SCEN-02 rewritten to include all three; (2) "reliability features" (item 5) had no dedicated requirement beyond error-response formatting — added NFR-09 for concurrency-safe analytics counters and a real DB health check.
**Scope of this baseline:** application (greenfield) + orchestration/governance system (all scenarios)

**Normalized source requirement:**
> Build a production-minded URL-shortener prototype that demonstrates governed, controlled, end-to-end agentic software engineering — not just AI-assisted coding.

---

## 0. Requirement Traceability Matrix (original assessment → this baseline)

| # | Original assessment item | Covered by |
|---|---|---|
| 1 | Working URL shortener service from scratch | FR-01…FR-08 |
| 2 | Agentic execution model turning requirements into reviewable outputs | ORCH-01 |
| 3 | Requirement understanding, ambiguity identification, task decomposition, multi-step execution, output generation & validation | ORCH-02, ORCH-03, ORCH-04, ORCH-05 |
| 4 | Cover greenfield + brownfield (enhancements, refactoring, **or** bug fixes) | SCEN-01, SCEN-02 (revised to include a refactor + a bug-fix element, not enhancement only — see A08) |
| 5 | Core APIs, analytics, reliability, unit/integration tests, documentation | FR-01…08, NFR-04, NFR-05, **NFR-09**, NFR-07, SUBMIT-02…07, OpenAPI/Swagger (§4 Scope) |
| 6 | Orchestration layer: stateful, non-linear, explicit dependency graph, sequential+parallel, synchronization | ORCH-06, ORCH-07, ORCH-08, ORCH-09 |
| 7 | Governance: approval checkpoints, bounded retries, fallback, rollback, safe stop, security/compliance guardrails, change-control | GOV-01…GOV-07 |
| 8 | Preserve cross-stage context, decision history, traceability, audit evidence | TRACE-01…TRACE-04 |
| 9 | Metrics: success rate, retry frequency, rollback frequency, MTTR, latency | METRIC-01 |
| 10 | Dynamic replanning on upstream change | ORCH-10 |
| 11 | Three scenarios: greenfield, brownfield, ambiguous | SCEN-01, SCEN-02, SCEN-03 |
| 12 | Submission: prototype, architecture overview, setup, testing approach, limitations, trade-offs, final summary | SUBMIT-01…SUBMIT-07 |

This matrix is the direct answer to "are we covering everything" — every original item now has at least one requirement ID behind it, and every requirement ID will in turn map to a build task (Phase 6) and a test (Phase 8).

## 1. Business Objective

Demonstrate that a software requirement can be taken through a governed, auditable, agent-assisted delivery process — interpreted, decomposed, designed, implemented, tested, reviewed, and released — with human accountability preserved at every material decision point. The URL shortener is the vehicle; the orchestration/governance system is the actual subject of assessment.

## 2. Problem Statement

Two problems, both in scope:

1. **Application problem:** users need to shorten URLs, have them redirect reliably, and see privacy-respecting analytics, without the service becoming a vector for abuse.
2. **Process problem:** "AI-assisted coding" alone doesn't demonstrate controlled engineering. The assessment requires evidence of a *governed* process — explicit gates, bounded autonomy, retry/rollback/safe-stop, traceability, and metrics — applied to real, non-trivial engineering work (not a toy pipeline running on a trivial task).

## 3. Actors

| Actor | Description |
|---|---|
| **API Consumer** | Any client calling the REST API to create/inspect/manage short URLs. |
| **End User (link clicker)** | Anyone who follows a short link and is redirected. |
| **Reviewer / Operator** | Runs the service locally, exercises the API via Swagger, and is the actual human approver at all three workflow gates — not a simulated persona. |
| **Orchestrator** | Loads the dependency graph, maintains workflow state, routes tasks, enforces policy, pauses for approval, handles retry/rollback/replanning — does not itself produce engineering artifacts. |
| **Agents** | Requirement Analysis, Planning, Architecture, Development, Test, Security/Quality Review, Documentation/Release — each produces one stage's artifact under the orchestrator's control. |

## 4. Scope

**Application track (in scope):**
- Create/redirect/inspect/analytics/expire/disable/custom-alias for short URLs; health check.
- URL safety controls at creation time (scheme allowlist, SSRF/private-network blocking).
- SQLite persistence via SQLAlchemy, Alembic migrations.
- Deterministic, offline-capable execution — no API key required to run or evaluate.

**Orchestration/governance track (in scope, first-class — not incidental tooling):**
- A dependency-graph-driven orchestrator with persisted state, non-linear routing, parallel branches, and an explicit join.
- Seven agents (§7 of master brief) with a common contract (inputs/outputs/allowed tools/entry-exit criteria/retry eligibility).
- Three enforced human approval gates with persisted approval records.
- Bounded retry, rollback, fallback (deterministic-mode), and safe-stop behavior.
- Dynamic, dependency-aware replanning (not full restart).
- Decision lineage, workflow event log, and prototype reliability metrics.
- Three demonstrated scenarios: greenfield, brownfield, ambiguous.

## 5. Out of Scope

Explicitly deferred, per binding assumption §3.19 and the "do not overengineer" list (§4 of master brief):

- User accounts, authentication, authorization, or link ownership (application-level).
- Rate limiting, unless selected as part of the ambiguous-security scenario's approved interpretation.
- Hard delete of links (status changes/disabling only).
- Custom frontend UI (Swagger is the UI).
- Any cloud/production infrastructure (Kubernetes, multi-region, service mesh, event streaming, vector DB/RAG).
- Full DNS-rebinding protection (documented as a production enhancement, not implemented).
- Live LLM execution as a hard requirement (optional; deterministic mode must fully satisfy every requirement in this document on its own).
- A heavy third-party agent framework — the orchestrator is custom, per binding assumption §3.11.

## 6. Functional Requirements — Application

| ID | Requirement | Notes |
|---|---|---|
| FR-01 | Create a short URL: `POST /api/v1/urls` accepting original URL, optional custom alias, optional expiry; returns short code, short URL, original URL, created/expiry timestamps, status. | |
| FR-02 | Redirect: `GET /{short_code}` resolves an active code, records an analytics event, and issues a redirect; returns a controlled error for unknown/disabled/expired codes. | HTTP 307 — see A02. |
| FR-03 | Retrieve URL details: `GET /api/v1/urls/{short_code}` returns original URL, code, timestamps, status, click count, last-accessed time. | |
| FR-04 | Retrieve analytics: `GET /api/v1/urls/{short_code}/analytics` returns total clicks, created/last-accessed timestamps, click-event timestamps, optional referrer domain, optional broad user-agent category. No IP address or precise geolocation is ever collected. | |
| FR-05 | Expiry: configurable expiry; expired links do not redirect (controlled error) but remain visible via the info API. | |
| FR-06 | Disable a link: `PATCH /api/v1/urls/{short_code}` supports controlled status transitions. Hard delete not implemented. | |
| FR-07 | Custom alias: validated for allowed characters, reserved names, max length, uniqueness. | |
| FR-08 | Health check: `GET /health` reports application status, database status, execution mode, version. | |

## 7. Functional Requirements — Agentic Execution Model

| ID | Requirement |
|---|---|
| ORCH-01 | The system SHALL implement an agentic execution model — Requirement Analysis, Planning, Architecture, Development, Test, Security/Quality Review, Documentation/Release agents coordinated by an SDLC Orchestrator — transforming a raw requirement into reviewable, versioned engineering artifacts at each stage. |
| ORCH-02 | The Requirement Analysis Agent SHALL produce, per requirement: normalized requirement, FRs/NFRs, ambiguities, assumptions, scope/out-of-scope, acceptance criteria, risks. |
| ORCH-03 | The Planning Agent SHALL decompose the normalized requirement into a work breakdown with dependencies, sequencing, parallelizable tasks, priorities, and validation checkpoints. |
| ORCH-04 | The orchestrator SHALL execute a multi-stage workflow (§9 workflow graph, master brief) where each stage produces and validates its own artifact before handing off to the next. |
| ORCH-05 | Every agent output SHALL be validated against entry/exit criteria before acceptance; invalid or incomplete output SHALL block progression, never pass silently. |
| ORCH-06 | The orchestration layer SHALL be **stateful**: workflow state (stage, retry count, rollback count, artifact versions) is persisted, not held only in memory, and a run SHALL be resumable from persisted state. |
| ORCH-07 | The orchestration layer SHALL be **non-linear**: it SHALL support branching, conditional routing (pass/fail), and revisiting earlier stages (retry, rollback, replanning) — not a fixed linear pipeline. |
| ORCH-08 | The orchestration SHALL be driven by an **explicit dependency graph in executable code/config**, not documentation only. |
| ORCH-09 | The orchestrator SHALL run independent stages **concurrently** (e.g. IMPLEMENTATION and TEST_DESIGN in parallel after architecture approval) with an explicit **synchronization/join** point before downstream stages proceed. |
| ORCH-10 | The orchestrator SHALL perform **dependency-aware dynamic replanning** when an upstream requirement/artifact changes: identify changed IDs, traverse the graph, mark only impacted downstream artifacts stale, preserve unaffected approved artifacts, re-execute only affected nodes, and request approval for high-impact changes. A full restart does not satisfy this requirement. |

## 8. Governance & Control Requirements

| ID | Requirement |
|---|---|
| GOV-01 | The workflow SHALL enforce at least three human approval gates (requirements, architecture, release) that block progression until a real, persisted approval decision exists. Auto-approval SHALL NOT be the default mode. |
| GOV-02 | Retries SHALL be bounded (max 2 per retryable stage) and apply only to transient/correctable failures; each retry records cause, corrective action, attempt number, and result. |
| GOV-03 | The system SHALL support **fallback** to deterministic (non-LLM) agents whenever live-LLM mode is unavailable/unconfigured, preserving identical workflow, gates, logging, and validation behavior. |
| GOV-04 | **Rollback** SHALL restore the last approved artifact versions, the last approved workflow checkpoint, and the previous validated code state (git/snapshot); it SHALL block release until re-approved. |
| GOV-05 | The workflow SHALL enter **SAFE_STOPPED** — and SHALL never be marked release-ready from that state — when retries are exhausted, a required approval is rejected, a critical security check fails, or artifact/state lineage is corrupted. |
| GOV-06 | Security/compliance guardrails SHALL include, at minimum: URL scheme allowlisting, SSRF/private-network blocking, cryptographically secure short-code generation, environment-variable-only secret handling, no stack-trace leakage, and an explicit denylist of agent actions (no direct production deploy, no bypassing approval gates, no destructive action without approval, no promoting a failed artifact, no secrets in prompts). |
| GOV-07 | **Change control**: the Development Agent SHALL NOT silently overwrite an already-approved artifact; a material change SHALL create a new artifact version, preserving the prior version for lineage. |

## 9. Traceability & Audit Requirements

| ID | Requirement |
|---|---|
| TRACE-01 | Workflow context (inputs, decisions, intermediate outputs) SHALL persist across all stages of one run, not be reconstructed per stage. |
| TRACE-02 | Every material decision (agent choice, retry, rollback, gate outcome, replanning decision) SHALL be recorded as an immutable event: actor, stage, inputs, outputs, decision, reason, timestamp. |
| TRACE-03 | Every requirement in this document SHALL be traceable to the artifact(s) and automated test(s) that implement/verify it (extended by a requirement-to-test matrix in Phase 8). |
| TRACE-04 | Audit evidence for each scenario run SHALL be retained as versioned artifacts under `artifacts/sample-runs/`, sufficient for a reviewer to reconstruct what happened without re-running the workflow. |

## 10. Metrics Requirements

| ID | Requirement |
|---|---|
| METRIC-01 | The system SHALL compute and expose, per run and in aggregate: workflow success rate, retry frequency, rollback frequency, MTTR, end-to-end latency, agent-step latency, approval waiting time, failed-stage frequency, artifact first-pass acceptance rate, replanning count, stale-artifacts-regenerated count, unaffected-artifacts-preserved count. These are clearly labelled as **prototype-scale metrics**, not production SLIs. |

## 11. Scenario Requirements

| ID | Requirement |
|---|---|
| SCEN-01 | **Greenfield** — full workflow graph executed end to end for the initial build; tagged `v1.0.0-greenfield`. |
| SCEN-02 | **Brownfield** — enhance the greenfield baseline without breaking existing links or API contracts, demonstrating all three change types named in the original assessment: (a) **enhancement** — configurable expiry range (1–365 days, replacing the fixed 30-day default) and link disabling; (b) **refactoring** — extract status/expiry-transition logic out of the request handler into a dedicated, independently-testable domain function as part of making it configurable; (c) **bug fix** — regression testing against the greenfield baseline is expected to surface at least one real defect (e.g. an edge case in expiry-boundary comparison or status-transition validation), which is then fixed under change control with a regression test added. Demonstrate impact analysis, migration, backward compatibility, full regression suite, and rollback capability; tagged `v1.1.0-brownfield`. |
| SCEN-03 | **Ambiguous** — submit "make shortened links more secure"; Requirement Analysis Agent enumerates ≥5 candidate interpretations (stronger short codes, malicious-URL blocking, SSRF controls, expiry, auth, rate limiting, ownership, abuse reporting); workflow pauses at Gate 1 for real clarification/approval before any implementation; approved interpretation is implemented selectively. |

## 12. Non-Functional Requirements — Application

| ID | Requirement |
|---|---|
| NFR-01 | **Security:** URL scheme allowlist (`http`/`https` only); SSRF protections blocking localhost, loopback, private IPv4/IPv6, link-local, and common cloud-metadata addresses at creation time. |
| NFR-02 | **Security:** Short codes generated with a cryptographically secure RNG (`secrets`), not a predictable counter or weak PRNG. |
| NFR-03 | **Privacy:** Analytics never store IP address or precise geolocation. |
| NFR-04 | **Reliability:** Structured, stable error codes and correlation IDs on every error response; no stack traces exposed to API consumers. |
| NFR-05 | **Observability:** Structured JSON logs; every workflow-relevant event persisted, not just printed. |
| NFR-06 | **Portability:** Runs fully via `docker compose up --build`, no external network dependency, no required API key. |
| NFR-07 | **Testability:** Automated unit/integration/negative tests for every FR above; target ≥80% coverage as a signal, not a sole quality gate. |
| NFR-08 | **Auditability:** Every material engineering decision is logged with input/output artifacts, decision, and reason. |
| NFR-09 | **Reliability:** Click-count increments and last-accessed updates on `short_urls` SHALL be atomic/consistent under concurrent redirect requests (DB-level atomic update or transaction) — concurrent hits on the same short code SHALL NOT lose updates. The `/health` endpoint's database check SHALL reflect real connectivity, not a hardcoded "ok". |

## 13. Submission / Deliverable Requirements

| ID | Requirement |
|---|---|
| SUBMIT-01 | Runnable prototype (`docker compose up --build`) in a public GitHub repository. |
| SUBMIT-02 | Architecture overview (`docs/architecture/`): components, workflow graph, data model, security model. |
| SUBMIT-03 | Setup instructions: README quick start + `REVIEWER_GUIDE.md`. |
| SUBMIT-04 | Testing approach (`docs/testing/`): test strategy, requirement-to-test traceability, coverage report. |
| SUBMIT-05 | Known limitations documented explicitly. |
| SUBMIT-06 | Trade-offs and alternatives considered documented (ADRs in `docs/decisions/`). |
| SUBMIT-07 | Final engineering summary: what was built, why, how, decisions, assumptions, risks, validation performed, production backlog. |

## 14. Constraints

- Python 3.12, FastAPI, Uvicorn, SQLAlchemy, SQLite (default), Alembic, Pytest, Docker/Compose — per binding assumptions.
- Deterministic agent execution must fully cover reviewer needs without any LLM API key.
- No external company-specific compliance standard is invoked; controls are labelled as general secure-engineering practice.
- Repository will be public — no confidential material, secrets, or proprietary content may ever be committed.
- Custom orchestrator (state machine + dependency graph), not a heavy third-party agent framework.

## 15. Dependencies

- None on external paid services. Optional live-LLM mode would depend on an external provider API key but is never required for any requirement in this document to be satisfied.

## 16. Assumptions

- A01 — SQLite is sufficient for the prototype; a production evolution path (e.g. Postgres) is documented, not implemented.
- A02 — "Temporary redirect" (FR-02) means HTTP 307, preserving method semantics and signalling the mapping is not permanently cacheable — appropriate given links can be disabled/expired.
- A03 — "Broad user-agent category" means a coarse classification (e.g. `browser`/`bot`/`other`), not the raw User-Agent string.
- A04 — Reserved short-code names (FR-07) include at minimum `api`, `health`, `docs`, `openapi.json`, `redoc`.
- A05 — "Version" in the data model/health endpoint means application/release version, distinct from the per-record optimistic-concurrency `version` field on `short_urls`.
- A06 — "Reviewable engineering outputs" (item 2) means each stage's artifact is a real file under version control (requirements doc, ADRs, code diffs, test reports), not a chat transcript.
- A07 — The three human approval gates are approved by the actual person reviewing this session in chat — not a simulated or auto-approved persona — in normal execution mode.
- A08 — Item 4's "enhancements, refactoring, or bug fixes" is read as: the single brownfield scenario should exhibit all three change types (not three separate scenarios), since the master brief names only one brownfield scenario (expiry + disabling). SCEN-02 is written accordingly.

## 17. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Scope is large relative to time available | Incomplete evidence at deadline | Priority-ordered build (P0 app → P0 orchestration core → scenarios → docs); prioritize completeness of evidence per binding assumption #1 |
| Orchestration requirements (§7–§10) are easy to under-build relative to the application | Assessment's actual subject (governed agentic process) under-delivered | This baseline now carries explicit IDs (ORCH/GOV/TRACE/METRIC/SCEN) that Phase 6 build plan and Phase 8 tests must trace to |
| SSRF allowlist/denylist logic is easy to get subtly wrong | Security control gap | Dedicated unit + negative test suite (`tests/security`) |
| Public repo exposure | Leaking secrets/internal material | `.gitignore` from the start; explicit secret scan before any push; nothing pushed until release gate |

## 18. Acceptance Criteria

- All FR-01–FR-08 and NFR-01–NFR-09 implemented and covered by automated tests.
- SCEN-02 demonstrably contains a refactor and a fixed regression bug, not only a feature enhancement.
- All ORCH-01–ORCH-10 and GOV-01–GOV-07 demonstrated in running code (not documentation-only) and covered by orchestration tests.
- All TRACE-01–TRACE-04 and METRIC-01 implemented and inspectable (persisted events, generated metrics report).
- All three scenarios (SCEN-01/02/03) executed with retained evidence under `artifacts/sample-runs/`.
- All SUBMIT-01–SUBMIT-07 deliverables present in the repository.
- `docker compose up --build` starts the service with no manual steps and no API key; `/health`, `/docs`, `/openapi.json` reachable.
- Data persists across a container restart (volume-backed SQLite).
- This document approved at Human Gate 1 before architecture work proceeds.

---
*Produced by: Requirement Analysis Agent (deterministic mode) — Phase 1 of the SDLC Orchestrator. Revised (v2) in direct response to reviewer feedback confirming coverage against the original assessment items.*
