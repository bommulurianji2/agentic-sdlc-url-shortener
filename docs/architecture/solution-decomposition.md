# Solution Decomposition — Phase 2

**Status:** DRAFT — informational (no dedicated approval gate between Phase 2 and Phase 3 per master brief; feeds directly into Phase 3 architecture)
**Input:** requirements-baseline.md v3 (Gate 1 approved)

For each module: purpose, inputs, outputs, logic, dependencies, testability, and which requirement IDs it exists to satisfy. Repository path is included so this maps directly onto Phase 6's build plan.

---

## 1. URL API — `app/api/`

- **Purpose:** REST endpoints for creating, inspecting, and managing short URLs.
- **Requirement IDs:** FR-01, FR-03, FR-05, FR-06, FR-07, FR-08
- **Inputs:** HTTP requests (JSON bodies, path/query params).
- **Outputs:** JSON responses — URL resource representations, or structured errors (§16 error contract).
- **Logic:** Pydantic request validation → delegate to Persistence + Security validation → map domain result to response schema.
- **Dependencies:** Persistence, Security validation, Analytics (read path).
- **Testability:** integration tests via FastAPI `TestClient`; OpenAPI schema contract check.

## 2. Redirect — `app/api/` (separate router from JSON API)

- **Purpose:** Resolve a short code and issue an HTTP redirect.
- **Requirement IDs:** FR-02, FR-05, FR-06
- **Inputs:** `GET /{short_code}`, optional `Referer`/`User-Agent` headers.
- **Outputs:** HTTP 307 redirect, or a structured error (unknown/expired/disabled).
- **Logic:** lookup → status/expiry check → record click event → redirect. URL is **not** re-validated for SSRF here — validation happens once, at creation (FR-01), not on every redirect.
- **Dependencies:** Persistence, Analytics.
- **Testability:** integration tests (valid/expired/disabled/unknown codes) + a concurrency test for NFR-09.

## 3. Analytics — `app/services/analytics.py`

- **Purpose:** Record and expose privacy-conscious click analytics.
- **Requirement IDs:** FR-04, NFR-03, NFR-09
- **Inputs:** click events from the Redirect module (timestamp, referrer domain, coarse UA category, correlation ID).
- **Outputs:** aggregated analytics response; `click_events` rows.
- **Logic:** on each redirect, insert a `click_event` row and atomically increment `short_urls.click_count`/`last_accessed` (single UPDATE with an atomic increment, not read-modify-write in application code). Referrer/UA are reduced to coarse categories before storage — raw values are never persisted.
- **Dependencies:** Persistence.
- **Testability:** unit tests for UA-categorization/referrer-domain extraction; integration test asserting correct count after N concurrent redirects.

## 4. Persistence — `app/database/`, `app/repositories/`

- **Purpose:** Data access for `short_urls`/`click_events` (app) and `workflow_runs`/`workflow_events`/`artifacts`/`approvals` (orchestration) — two schemas, one module, since both need the same migration discipline.
- **Requirement IDs:** underlies all FR/ORCH/GOV/TRACE IDs that persist state.
- **Inputs:** domain calls (create/read/update) from API and orchestration code.
- **Outputs:** SQLAlchemy ORM rows; Alembic migration scripts per schema change.
- **Logic:** repository pattern over SQLAlchemy models; brownfield migrations are additive (new nullable columns / new tables), never destructive to existing rows.
- **Dependencies:** SQLite (default), swappable via `DATABASE_URL`.
- **Testability:** unit tests against repository methods using a temp SQLite DB per test.

## 5. Security validation — `app/services/url_safety.py`

- **Purpose:** Enforce scheme allowlisting, SSRF/private-network blocking, and secure short-code generation at creation time.
- **Requirement IDs:** NFR-01, NFR-02
- **Inputs:** raw `original_url`, requested custom alias.
- **Outputs:** validated URL, or a specific rejection (`INVALID_URL` / `UNSAFE_SCHEME` / `BLOCKED_PRIVATE_DESTINATION`).
- **Logic:** scheme check → hostname resolution → loopback/private-IPv4/IPv6/link-local/cloud-metadata denylist → alias character/reserved-name/length/uniqueness check. Pure function — no I/O side effects beyond DNS resolution — so it's independently testable and reusable by the Security & Quality Review Agent.
- **Dependencies:** none beyond the standard library (`ipaddress`, `secrets`, `urllib.parse`).
- **Testability:** dedicated `tests/security` unit + negative tests (localhost, `127.0.0.1`, `169.254.169.254`, `::1`, `file://`, `javascript:`, etc.).

## 6. Workflow orchestration — `agentic/orchestrator.py`, `agentic/graph.py`, `agentic/state.py`, `agentic/policies.py`

- **Purpose:** Stateful, non-linear, dependency-graph-driven execution engine with parallel branches and an explicit join.
- **Requirement IDs:** ORCH-06, ORCH-07, ORCH-08, ORCH-09
- **Inputs:** a `WorkflowContext` (requirement, scenario type, current stage, artifact references).
- **Outputs:** persisted `workflow_runs`/`workflow_events` rows, stage transitions, next-stage routing decisions.
- **Logic:** `graph.py` defines nodes/edges in code — **including the corrected `SECURITY_REVIEW` fail-edge** (critical → `SAFE_STOP`, non-critical → `RETRY_EVALUATION`) per your confirmation on the master-prompt gap; `orchestrator.py` evaluates entry/exit criteria and invokes the right agent; `policies.py` enforces governance rules.
- **Dependencies:** Agents, Approval, Retry/Rollback, Replanning, Artifact management, Metrics.
- **Testability:** `tests/orchestration` — parallel-branch execution, join behavior, state persistence/resume, retry/rollback/safe-stop.

## 7. Agents — `agentic/agents/`

- **Purpose:** The 7 agent roles behind a common contract.
- **Requirement IDs:** ORCH-01, ORCH-02, ORCH-03, ORCH-04, ORCH-05
- **Inputs:** `WorkflowContext` + prior-stage artifacts.
- **Outputs:** `AgentResult` (status, output_artifacts, decisions, risks, retryable, requires_approval, metrics, error).
- **Logic:** deterministic (rule-based/templated) by default; an optional `llm_provider.py` hook exists for live-LLM mode but is never required for any requirement to be satisfied.
- **Dependencies:** Artifact management, invoked by Workflow orchestration.
- **Testability:** one unit test per agent (fixed input → output matches schema/expected decisions) + a contract test that every agent satisfies the common interface.

## 8. Approval — `agentic/approvals.py`, `scripts/approve_gate.py`

- **Purpose:** Three enforced human gates with persisted approval records.
- **Requirement IDs:** GOV-01
- **Inputs:** gate name, workflow ID, artifact versions under review.
- **Outputs:** `approvals` table row (approver, decision, comments, artifact versions, timestamp).
- **Logic:** CLI prompt in normal mode; `--auto-approve-demo` exists only in the clearly separate `scripts/run_demo.py` path, never the default.
- **Dependencies:** Persistence; blocks Workflow orchestration until resolved.
- **Testability:** orchestration tests for gate-pause, approval, and rejection paths.

## 9. Artifact management — `agentic/artifact_store.py`

- **Purpose:** Version and store every stage's output artifact; never silently overwrite an approved version.
- **Requirement IDs:** GOV-07, TRACE-03, TRACE-04
- **Inputs:** artifact content + type + workflow ID.
- **Outputs:** `artifacts` table row (version, checksum, content path).
- **Logic:** write-once versioned storage under `artifacts/`; checksum for integrity; a material change always creates a new version.
- **Dependencies:** Persistence.
- **Testability:** unit tests for version-increment-on-change, immutability of approved versions, checksum verification.

## 10. Retry and rollback — `agentic/retry.py`, `agentic/rollback.py`

- **Purpose:** Bounded retry, rollback to last-approved state, safe-stop.
- **Requirement IDs:** GOV-02, GOV-04, GOV-05
- **Inputs:** stage-failure event, current retry count.
- **Outputs:** retry decision (retry/rollback/safe-stop), rollback record.
- **Logic:** `retry.py` enforces the max-2 bound and retryability classification; `rollback.py` restores last-approved artifact versions plus the underlying git/snapshot code state.
- **Dependencies:** Workflow orchestration, Artifact management, git.
- **Testability:** orchestration tests using the required failure-injection flags (`--inject-failure`, `--inject-permanent-failure`).

## 11. Replanning — `agentic/replanning.py`

- **Purpose:** Dependency-aware selective replanning — not a full restart.
- **Requirement IDs:** ORCH-10
- **Inputs:** changed requirement/artifact, prior dependency graph, prior artifact versions.
- **Outputs:** revised plan; explicit stale-vs-preserved artifact lists.
- **Logic:** diff old/new requirement IDs → traverse `graph.py` edges → mark only downstream-affected nodes stale → preserve the rest → re-invoke only affected agents.
- **Dependencies:** Workflow orchestration, Artifact management.
- **Testability:** a dedicated test reproducing the master brief's 30-day → 1–365-day expiry change, asserting the exact expected stale/preserved artifact sets (§13 master brief).

## 12. Metrics — `agentic/metrics.py`, `scripts/generate_metrics.py`

- **Purpose:** Prototype reliability metrics.
- **Requirement IDs:** METRIC-01
- **Inputs:** the `workflow_events` stream.
- **Outputs:** computed metrics (success rate, retry/rollback frequency, MTTR, latencies, etc.).
- **Logic:** aggregate queries over `workflow_events`/`workflow_runs`; formulas fixed in Phase 5.
- **Dependencies:** Persistence, Workflow orchestration.
- **Testability:** unit tests against a seeded set of `workflow_events` producing known expected values.

## 13. Testing — `tests/`

- **Purpose:** Automated verification for both the app and the orchestration layer.
- **Requirement IDs:** NFR-07, TRACE-03, and the verification half of every ID in this document.
- **Inputs:** application + orchestration code.
- **Outputs:** `tests/unit`, `tests/integration`, `tests/orchestration`, `tests/security`; coverage report; requirement-to-test matrix.
- **Logic:** pytest + pytest-cov; ruff/black/mypy/pip-audit in CI.
- **Dependencies:** every other module (it tests them).
- **Testability:** n/a — this module *is* the testability mechanism; its own correctness is verified by CI passing.

## 14. Documentation — `docs/`, root-level `.md` files

- **Purpose:** The submission deliverables.
- **Requirement IDs:** SUBMIT-02…SUBMIT-07
- **Inputs:** all artifacts produced by every other module.
- **Outputs:** README, REVIEWER_GUIDE, AI_USAGE, SECURITY, CHANGELOG, architecture docs, ADRs, final engineering summary.
- **Logic:** the Documentation & Release Agent synthesizes these from persisted artifacts/decisions rather than writing them ad hoc.
- **Dependencies:** Artifact management (source of truth), all modules.
- **Testability:** reviewer-experience validation (§23 master brief) — the five-minute path is actually walked, not just described.

---

## Module Dependency Summary

```
URL API ──┬─> Security validation
          ├─> Persistence
          └─> Analytics (read)

Redirect ──> Persistence, Analytics (write)

Workflow orchestration ──┬─> Agents
                          ├─> Approval
                          ├─> Artifact management
                          ├─> Retry and rollback
                          ├─> Replanning
                          └─> Metrics

Agents, Approval, Retry/rollback, Replanning, Metrics ──> Persistence

Testing ──> (depends on) every module above
Documentation ──> (depends on) every module's artifacts
```

No module has a dependency cycle back to Testing or Documentation — both are pure consumers, which is what keeps them addable/regenerable without touching runtime code.

---
*Produced by: Planning Agent (deterministic mode) — Phase 2 of the SDLC Orchestrator.*
