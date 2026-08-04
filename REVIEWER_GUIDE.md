# Reviewer Guide

## Prerequisites

- Docker Desktop (or any Docker + Compose v2 install). Nothing else — no Python, no API key, no account of any kind.

## Startup

```bash
git clone https://github.com/bommulurianji2/agentic-sdlc-url-shortener.git
cd agentic-sdlc-url-shortener
docker compose up --build
```

Watch the logs for three Alembic migrations applying, then `Uvicorn running on http://0.0.0.0:8000`. Then:

- Swagger UI: http://localhost:8000/docs
- Health: http://localhost:8000/health → `{"status":"ok","database":"connected","execution_mode":"deterministic","version":"1.0.0"}`
- OpenAPI: http://localhost:8000/openapi.json
- **Live demo UI**: http://localhost:8000/demo — the fastest way to see everything below in one place; skip ahead to "Live demo UI" if you want the guided version before doing this manually.

## API test sequence (via Swagger, or curl)

```bash
curl -X POST http://localhost:8000/api/v1/urls -H "Content-Type: application/json" \
  -d '{"original_url": "https://example.com/some/long/path"}'
# -> {"short_code": "...", "short_url": "...", "status": "active", ...}

curl -L http://localhost:8000/<short_code>          # redirects (307)
curl http://localhost:8000/api/v1/urls/<short_code>/analytics   # click recorded

# Negative cases worth trying:
curl -X POST http://localhost:8000/api/v1/urls -d '{"original_url": "http://127.0.0.1/x"}'   # BLOCKED_PRIVATE_DESTINATION
curl -X POST http://localhost:8000/api/v1/urls -d '{"original_url": "ftp://example.com"}'    # UNSAFE_SCHEME
curl http://localhost:8000/does-not-exist                                                     # UNKNOWN_SHORT_CODE
```

## Test suite

```bash
docker compose exec api pytest -v
docker compose exec api pytest --cov=app --cov=agentic --cov-report=term-missing
```

117 tests, 96% coverage. `tests/security/` (SSRF/scheme/rate-limit), `tests/orchestration/` (graph, agents, full workflow runs, replanning), `tests/integration/` (API + brownfield regression), `tests/unit/` (everything else).

## Scenario sequence

Run all three unattended:

```bash
docker compose exec api python scripts/run_demo.py --auto-approve-demo
```

Or one at a time, with the **real** human-approval flow (no auto-approve):

```bash
docker compose exec api python scripts/run_greenfield.py
# -> pauses, prints the exact next command:
docker compose exec api python scripts/approve_gate.py <workflow_id> requirements approved
docker compose exec api python scripts/run_greenfield.py --workflow-id <workflow_id>
# -> repeats for the architecture and release gates
```

This is the actual GOV-01 behavior — it isn't simulated. Re-running with `--workflow-id` resumes from persisted state in a fresh process, which is the literal ADR-009 resumability claim.

Then:

```bash
docker compose exec api python scripts/run_brownfield.py --auto-approve-demo
```

Watch for the **dynamic replanning demonstration** printed after completion — it shows the exact requirement ID that changed and which artifact types were marked stale, matching the master brief's own worked example (30-day fixed expiry → 1–365-day configurable).

```bash
docker compose exec api python scripts/run_ambiguous.py --auto-approve-demo
```

Watch for the **ambiguity analysis** — 8 candidate interpretations printed before any implementation happens, plus which one was approved and why.

## Failure-injection demonstration (retry → rollback → safe-stop)

```bash
docker compose exec api python scripts/run_greenfield.py --auto-approve-demo --inject-failure test_execution
```

Expected: `TEST_EXECUTION` fails twice (bounded retry, GOV-02), then rolls back and reaches `SAFE_STOPPED` — never `COMPLETED`.

```bash
docker compose exec api python scripts/run_greenfield.py --auto-approve-demo --inject-permanent-failure
```

Expected: the Security Review agent reports a critical finding and the workflow goes **straight** to `SAFE_STOPPED` — zero retries spent (ADR-007's corrected fail-path).

## Live demo UI

Everything above, in one browser tab, side by side:

```
http://localhost:8000/demo
```

**Left panel** — the real application. Create a link (full form: URL, custom alias, expiry), see it appear in the list, click **Visit** to actually redirect, **Analytics** to see the recorded click, **Disable**/**Enable** to toggle it. Every action calls the exact same endpoints as the API test sequence above — nothing new on that side.

**Right panel**, two tabs:
- **Request Pipeline** (default) — the real steps your last left-panel action just took through the actual application code, revealed as they complete. Deliberately *not* labeled as agents, because it isn't agents — it's the deterministic code path, made visible.
- **Agentic Governance** — pick a scenario, tick the failure-injection checkboxes if you want, click **Run new scenario**, and watch the real orchestrator graph advance live: each stage lights up as it completes, a pending gate shows **Approve**/**Reject** buttons right there, and a `SAFE_STOPPED` or `COMPLETED` outcome renders as a banner with the real reason from the event log. You can also paste in a workflow ID from a CLI-started run (e.g. one you resumed manually above) to watch it the same way.

This is not a separate visualization layer — clicking **Run**/**Approve** in the browser launches the exact same `scripts/run_<scenario>.py` you'd run by hand (see [ADR-013](docs/decisions/ADR-013-interactive-demo-ui.md)), so anything true of the CLI flow is true here too, including the ~15-30 second wait while the real test suite executes after approving Gate 2.

Either way, check `agentic.state.can_release()` would return `False` for that run — a `SAFE_STOPPED` workflow can never be tagged/released.

## Reading the evidence

- [`artifacts/sample-runs/`](artifacts/sample-runs/) has one retained JSON per scenario (workflow ID, final status, retry/rollback/failure counts, revision).
- For live detail on any run, query the SQLite file directly:
  ```bash
  docker compose exec api python -c "
  from app.database.session import SessionLocal
  from agentic.models import WorkflowEvent
  db = SessionLocal()
  for e in db.query(WorkflowEvent).order_by(WorkflowEvent.timestamp).all():
      print(e.timestamp, e.stage, e.event_type, e.reason)
  "
  ```
- Requirement-to-test mapping: [`docs/testing/traceability-matrix.md`](docs/testing/traceability-matrix.md).
- Every architecture decision and its rejected alternatives: [`docs/decisions/`](docs/decisions/) (12 ADRs).

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| `docker compose up --build` fails downloading packages | Check your network/proxy; nothing in this repo needs an API key, only package registries |
| A scenario script prints `WAITING_FOR_*` and exits | Correct behavior — that's a real human gate. Approve it, then re-run with `--workflow-id` |
| Re-running a scenario without `--workflow-id` | Starts a **new** workflow — expected, not a bug, if you wanted to resume the old one, pass its ID |
| `pytest` inside the container finds 0 tests | Shouldn't happen — `tests/` is copied into the image; if it does, rebuild with `--no-cache` |
| Rate limiting (`RATE_LIMIT_EXCEEDED`) during heavy manual testing | Default is 100 creates/min/IP (`RATE_LIMIT_PER_MINUTE`); raise it via environment if needed for exploration |
