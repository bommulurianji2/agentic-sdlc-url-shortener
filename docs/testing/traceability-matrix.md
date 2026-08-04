# Requirement-to-Test Traceability Matrix

**Status:** Phase 8 (Testing and validation) — TRACE-03, SUBMIT-04
**Source:** [requirements-baseline.md](../requirements/requirements-baseline.md) §0

Every requirement ID from the approved baseline, mapped to the test(s) that verify it. Current coverage: **96%** (`pytest --cov=app --cov=agentic`), 117/117 tests passing.

## Application — Functional Requirements

| ID | Requirement | Verified by |
|---|---|---|
| FR-01 | Create short URL | `tests/integration/test_urls_api.py` (create, custom alias, duplicate alias) |
| FR-02 | Redirect | `tests/integration/test_redirect.py` |
| FR-03 | Retrieve URL details | `tests/integration/test_urls_api.py::test_get_url_details` |
| FR-04 | Retrieve analytics | `tests/integration/test_urls_api.py` (analytics tests), `tests/unit/test_analytics.py` |
| FR-05 | Expiry | `tests/integration/test_redirect.py::test_redirect_expired_url_*`, `tests/integration/test_brownfield_regression.py` |
| FR-06 | Disable a link | `tests/integration/test_urls_api.py::test_disable_and_reenable_url`, `tests/integration/test_brownfield_regression.py` |
| FR-07 | Custom alias | `tests/integration/test_urls_api.py`, `tests/security/test_url_safety.py` (alias validation) |
| FR-08 | Health check | `tests/integration/test_health.py`, `tests/integration/test_health_degraded.py` |

## Application — Non-Functional Requirements

| ID | Requirement | Verified by |
|---|---|---|
| NFR-01 | Scheme allowlist + SSRF blocking | `tests/security/test_url_safety.py` (23 tests) |
| NFR-02 | Secure short-code generation | `tests/security/test_url_safety.py::test_short_code_*` |
| NFR-03 | No IP/geo in analytics | `tests/unit/test_analytics.py` (coarse categorization only) |
| NFR-04 | Structured errors + correlation IDs | `tests/integration/test_health_degraded.py::test_unexpected_exception_*` |
| NFR-05 | Structured JSON logs | `app/logging_config.py` (94% covered; format verified by inspection) |
| NFR-06 | Portable, no API key required | Docker validation (Phase 9) |
| NFR-07 | Test coverage ≥80% | This matrix + `--cov-report`: 96% actual |
| NFR-08 | Auditability | `tests/orchestration/test_orchestrator.py` (workflow_events assertions via `_log_event`) |
| NFR-09 | Concurrency-safe counters | `tests/integration/test_redirect.py::test_multiple_concurrent_redirects_*` |

## Orchestration — Agentic Execution Model

| ID | Requirement | Verified by |
|---|---|---|
| ORCH-01 | Agentic execution model | `tests/orchestration/test_agents.py` (all 7 agents exercised) |
| ORCH-02 | Requirement understanding + ambiguity ID | `test_agents.py::test_requirement_analysis_*` (greenfield/brownfield/ambiguous) |
| ORCH-03 | Task decomposition | `test_agents.py::test_planning_covers_every_requirement_id` |
| ORCH-04 | Multi-stage execution | `tests/orchestration/test_orchestrator.py` (full graph walk) |
| ORCH-05 | Output validation before acceptance | `tests/unit/test_artifact_store.py`, agent `validate()` calls in `test_agents.py` |
| ORCH-06 | Stateful / resumable | `run_greenfield.py --workflow-id` live verification (3 separate process invocations — see commit history) |
| ORCH-07 | Non-linear (branch/retry/rollback) | `test_orchestrator.py::test_retry_exhaustion_*`, `::test_critical_security_finding_*` |
| ORCH-08 | Explicit dependency graph in code | `tests/orchestration/test_graph.py::test_graph_has_no_structural_violations` |
| ORCH-09 | Real parallel branch + join | `test_orchestrator.py::test_full_greenfield_workflow_*` (IMPLEMENTATION/TEST_DESIGN run concurrently) |
| ORCH-10 | Dependency-aware replanning | `tests/orchestration/test_replanning.py` (3 tests) + live `run_brownfield.py` demonstration |

## Governance & Control

| ID | Requirement | Verified by |
|---|---|---|
| GOV-01 | 3 human approval gates | `test_orchestrator.py` (all 3 gates exercised: pause/approve/reject) |
| GOV-02 | Bounded retry (max 2) | `tests/unit/test_retry_rollback.py::test_retry_is_bounded_at_two` |
| GOV-03 | Deterministic fallback | ADR-004; all tests run in deterministic mode by default (no LLM key required) |
| GOV-04 | Rollback | `tests/unit/test_retry_rollback.py::test_rollback_supersedes_*` |
| GOV-05 | Safe-stop | `test_orchestrator.py::test_retry_exhaustion_leads_to_rollback_and_safe_stop`, `::test_critical_security_finding_safe_stops_*` |
| GOV-06 | Security/compliance guardrails | `tests/unit/test_policies.py` (denylist + skipped-test checks) |
| GOV-07 | Change control (no silent overwrite) | `tests/unit/test_artifact_store.py::test_approving_a_new_version_supersedes_*` |

## Traceability, Metrics, Scenarios

| ID | Requirement | Verified by |
|---|---|---|
| TRACE-01 | Cross-stage context persists | `WorkflowContext.artifacts` threading — exercised throughout `test_orchestrator.py` |
| TRACE-02 | Immutable decision events | `_log_event` calls asserted indirectly via retry/rollback/gate tests |
| TRACE-03 | This matrix | This document |
| TRACE-04 | Retained per-scenario evidence | `artifacts/sample-runs/*.json` (one per scenario, committed) |
| METRIC-01 | Prototype metrics | `tests/unit/test_metrics.py` (10 tests, 100% coverage of `agentic/metrics.py`) |
| SCEN-01 | Greenfield | `run_greenfield.py` live run → COMPLETED (sample evidence committed) |
| SCEN-02 | Brownfield | `run_brownfield.py` live run → COMPLETED; `test_brownfield_regression.py` (8 tests) |
| SCEN-03 | Ambiguous | `run_ambiguous.py` live run → COMPLETED; 8 interpretations printed, real clarification pause |

## Known Gaps (documented, not hidden)

- **MTTR** and **approval-waiting-time** metrics are not implemented (`agentic/metrics.py`'s `generate_report()` docstring says so explicitly) — a small prototype run doesn't naturally accumulate enough history to make these meaningful, and building them without real data would be more theater than signal.
- A few defensive branches (e.g. `graph.py`'s structural-error `raise` paths, `security_review_agent.py`'s `FileNotFoundError` fallback when a tool genuinely isn't installed) are intentionally not covered — they exist to fail loudly on a misconfiguration that unit tests can't realistically trigger without faking the misconfiguration itself.
