# Agentic SDLC URL Shortener

A URL shortener whose actual subject is not the URL shortener — it's the **governed agentic process** that built it: a custom dependency-graph orchestrator, seven deterministic agents, three enforced human approval gates, bounded retry, rollback, safe-stop, dependency-aware replanning, and full decision/audit traceability, applied to three real scenarios (greenfield, brownfield, ambiguous).

No API key is required to run, test, or evaluate anything in this repository. Every agent runs in deterministic mode by default.

## What this demonstrates

- **Requirement → reviewable engineering artifact**, at every stage — not just AI-assisted coding. See [`docs/requirements/requirements-baseline.md`](docs/requirements/requirements-baseline.md) §0 for a full traceability matrix from the original assessment's 12 requirement items down to specific requirement IDs, and [`docs/testing/traceability-matrix.md`](docs/testing/traceability-matrix.md) from there down to specific tests.
- **A real dependency graph and state machine** ([`agentic/graph.py`](agentic/graph.py), [`agentic/orchestrator.py`](agentic/orchestrator.py)) — not a linear script. One genuine parallel branch (implementation + test design run concurrently), conditional routing, retry, rollback, and safe-stop are all exercised by [`tests/orchestration/`](tests/orchestration/).
- **Three governed scenarios**, each independently runnable and each reaching a real `COMPLETED` state with retained evidence in [`artifacts/sample-runs/`](artifacts/sample-runs/):
  - **Greenfield** — the initial build.
  - **Brownfield** — configurable expiry (1–365 days), a genuine backward-compatible migration, a refactor, and a real regression bug caught by tests and fixed under change control before it was ever committed. Also demonstrates dependency-aware replanning.
  - **Ambiguous** — "make shortened links more secure" is decomposed into 8 candidate interpretations, and the workflow pauses for real human clarification before implementing the approved one.

## Architecture at a glance

```
┌─────────────────────────────────────────────────────────────┐
│  One container                                                │
│  ┌──────────────────────┐    ┌────────────────────────────┐  │
│  │ app/  (FastAPI)        │    │ agentic/ (orchestrator +    │  │
│  │ URL API + redirect     │    │ 7 agents), driven by         │  │
│  │ + analytics            │    │ scripts/run_*.py             │  │
│  └───────────┬────────────┘    └───────────┬─────────────────┘  │
│              └────────────┬────────────────┘                    │
│                           ▼                                     │
│              SQLAlchemy + Alembic + SQLite (volume)              │
└─────────────────────────────────────────────────────────────┘
```

Full detail: [`docs/architecture/architecture-overview.md`](docs/architecture/architecture-overview.md), [`docs/architecture/ai-dlc-design.md`](docs/architecture/ai-dlc-design.md), [`docs/architecture/detailed-technical-design.md`](docs/architecture/detailed-technical-design.md), and 12 ADRs in [`docs/decisions/`](docs/decisions/).

## Quick start

```bash
git clone https://github.com/bommulurianji2/agentic-sdlc-url-shortener.git
cd agentic-sdlc-url-shortener
docker compose up --build
```

Then:

```text
Swagger UI:      http://localhost:8000/docs
Health endpoint: http://localhost:8000/health
OpenAPI:         http://localhost:8000/openapi.json
```

## Live demo UI

```
http://localhost:8000/demo
```

A side-by-side reviewer view: the left panel is the real application (create/redirect/analytics/disable, using the exact endpoints above); the right panel has two tabs — **Request Pipeline** (the real deterministic steps your last action on the left just took) and **Agentic Governance** (pick a scenario, click Run, and watch the actual orchestrator graph advance node by node in real time, with live Approve/Reject buttons at each gate). Not part of the versioned `/api/v1/...` surface — see [ADR-013](docs/decisions/ADR-013-interactive-demo-ui.md) for why this exists alongside, not instead of, the CLI-only approval flow.

## Running the tests

```bash
docker compose exec api pytest -v
docker compose exec api pytest --cov=app --cov=agentic --cov-report=term-missing
```

125 tests, 96% coverage (target was 80%). See [`docs/testing/traceability-matrix.md`](docs/testing/traceability-matrix.md) for what each requirement ID is verified by.

## Running the scenarios

```bash
docker compose exec api python scripts/run_demo.py --auto-approve-demo   # all 3, unattended
docker compose exec api python scripts/run_greenfield.py                  # real CLI approval flow
docker compose exec api python scripts/run_brownfield.py
docker compose exec api python scripts/run_ambiguous.py
```

Full walkthrough, including retry/rollback/safe-stop failure injection and how to read the evidence: [`REVIEWER_GUIDE.md`](REVIEWER_GUIDE.md).

## Where the evidence lives

- [`artifacts/sample-runs/`](artifacts/sample-runs/) — one retained, real `COMPLETED` run per scenario.
- `workflow_events` / `workflow_runs` / `artifacts` / `approvals` tables (inside the running container's SQLite file) — the full audit trail for any run, including ones you execute yourself.
- Git history itself — e.g. the brownfield regression bug: introduced, caught by a real failing test, fixed under change control, all as separate, inspectable commits.

## Known limitations

- Deterministic agents use a fixed rule set tuned to this project's three known scenarios, not general-purpose natural-language understanding (see [ADR-004](docs/decisions/ADR-004-deterministic-agents.md)).
- The one parallel branch uses in-process threads, not true distributed parallelism ([ADR-010](docs/decisions/ADR-010-in-process-parallelism.md)).
- Replanning operates at artifact-type granularity, not sub-document granularity (documented in `agentic/replanning.py` and the brownfield scenario's own output).
- MTTR and approval-waiting-time metrics aren't implemented — noted explicitly in `agentic/metrics.py` rather than faked.
- No live-LLM mode is implemented (deterministic mode satisfies every requirement on its own; this was a P2/optional item — see [ADR-011](docs/decisions/ADR-011-agent-tool-allowlisting.md) for what would need to change if it were built).

Full list, trade-offs, and production backlog: see the final engineering summary (`docs/final-engineering-summary.md`, produced at release).

## AI usage

This project was built with Claude Code, working as the primary engineering execution assistant end to end — see [`AI_USAGE.md`](AI_USAGE.md) for what it did, what got corrected, and what stayed a human decision.
