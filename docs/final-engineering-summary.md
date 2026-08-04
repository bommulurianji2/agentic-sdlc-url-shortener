# Final Engineering Summary

**Status:** Phase 10 deliverable (SUBMIT-07)

## What was built

A URL shortener (FastAPI + SQLAlchemy + SQLite) whose actual subject is the governed agentic process that built it: a custom dependency-graph orchestrator (`agentic/orchestrator.py`, `agentic/graph.py`), 7 deterministic agents (`agentic/agents/`), 3 enforced human approval gates, bounded retry, rollback, safe-stop, dependency-aware replanning, and prototype reliability metrics — demonstrated across three scenarios (greenfield, brownfield, ambiguous), each independently runnable and each reaching a genuine `COMPLETED` state with retained evidence.

## Why it was built this way

The assessment's stated core expectation was to demonstrate *governed, controlled, end-to-end agentic software engineering — not just AI-assisted coding*. That framing drove every major decision: a custom, inspectable orchestrator over a third-party agent framework (ADR-001); deterministic agents as the fully-functional default, with live-LLM strictly optional (ADR-004); every governance control (gates, retry bounds, denylists, skip-test detection) implemented as executable code, not a written policy trusted to be followed (`agentic/policies.py`, `agentic/retry.py`).

## How it works

See `docs/architecture/architecture-overview.md`, `docs/architecture/ai-dlc-design.md`, and `docs/architecture/detailed-technical-design.md` for full detail. In short: a scenario script drives the orchestrator through the graph node by node, invoking the responsible agent, persisting state/events/artifacts after each step, and pausing at any of three gates until a real human decision is recorded. Re-running the script resumes from exactly that point, in a fresh process — verified live, not just claimed (see commit history for `scripts/run_greenfield.py`).

## Decisions and assumptions

12 ADRs (`docs/decisions/`) cover every material architecture decision with alternatives considered. Requirements-level assumptions are in `docs/requirements/requirements-baseline.md` §16. Two corrections to gaps found in the master brief's own specification are called out explicitly rather than silently patched: the missing `SECURITY_REVIEW` fail-path (ADR-007) and Gate 2's timing relative to the build plan (resolved as two touchpoints, per the reviewer's own choice).

## Risks and trade-offs

- **Artifact-type-granularity replanning** (not sub-document granularity) — `agentic/replanning.py`'s module docstring states this trade-off directly; finer preservation shows up at the file level inside `DevelopmentOutput.changed_files` instead.
- **In-process thread-based parallelism**, not distributed workers (ADR-010) — genuine concurrent execution with a real join, but not production-grade isolation.
- **Single SQLite file** for both application and orchestration tables (ADR-003) — simplest for a prototype; a documented future split is the production path if load ever required it.
- **Deterministic agents' fixed rule set** (ADR-004) — real governance and real code, but not general-purpose requirement understanding; explicitly out of scope, not hidden.

## Validation performed

117 tests, 96% coverage (target was 80%) — see `docs/testing/traceability-matrix.md` for the full requirement-to-test mapping. Beyond unit/integration tests, every major claim in this repository was validated by actually running it, not just writing it and assuming correctness:

- All three scenarios run live to `COMPLETED`, evidence retained in `artifacts/sample-runs/`.
- Resumability verified across three separate process invocations of `run_greenfield.py`, not just within one Python process.
- Retry-exhaustion→rollback→safe-stop and critical-security→safe-stop-without-retry both verified live via `--inject-failure`/`--inject-permanent-failure`.
- A real regression bug (brownfield's `expires_in_days` boundary validation) was caught by a test before it was ever committed, then fixed under change control.
- `docker compose up --build` validated end to end: `/health`/`/docs`/`/openapi.json` reachable, data persists across a container restart, the full test suite and a live scenario run both pass *inside* the container (which caught a real gap — the Dockerfile hadn't copied `tests/` at all).

## Known limitations

See `README.md`'s "Known limitations" section — restated here for completeness: fixed-rule-set deterministic agents (not general NLU); in-process (not distributed) parallelism; artifact-type-level (not sub-document-level) replanning granularity; MTTR and approval-waiting-time metrics not implemented (stated in `agentic/metrics.py`, not faked); no live-LLM mode built out; no workflow-approval REST API (CLI-only, by design — ADR-008).

## Production backlog

1. Split the application and orchestration databases (and move off SQLite) if concurrent scenario-run + live-traffic load ever became real.
2. Full DNS-rebinding protection (re-resolve and pin destination IPs at redirect time, not just at creation).
3. Real tool-allowlist enforcement for live-LLM mode, if that mode is ever built (ADR-011).
4. MTTR and approval-waiting-time metrics, once real usage produces enough workflow-event history for them to be meaningful.
5. A workflow-approval REST endpoint, if this became a multi-user system where CLI-only approval stopped being sufficient (ADR-008).
6. Sub-document-granularity replanning (mark specific sections of an artifact stale rather than the whole artifact type), if scenarios ever needed finer-grained evidence than the file-level preservation this prototype relies on.
