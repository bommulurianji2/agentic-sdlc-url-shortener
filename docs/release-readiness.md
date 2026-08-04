# Release Readiness Checklist — Phase 9

| Check | Status | Evidence |
|---|---|---|
| Clean-start Docker validation | ✅ | `docker compose up --build` from scratch; `/health`, `/docs`, `/openapi.json` all reachable |
| Data persists across restart | ✅ | Created a URL, `docker compose restart api`, record still present |
| Migrations apply cleanly | ✅ | 3 Alembic migrations run on every container start (idempotent) |
| Test suite (in container) | ✅ | 117/117 passing, 96% coverage |
| Scenario runs (in container) | ✅ | `run_greenfield.py --auto-approve-demo` → `COMPLETED` inside the actual container |
| Rollback / safe-stop validated | ✅ | Unit tests + live `--inject-failure`/`--inject-permanent-failure` |
| Secret-handling review | ✅ | Full history + working-tree scan, clean; no `.env` ever committed |
| CI (real, on GitHub Actions) | ✅ | 2/2 runs `success` — lint, type-check, tests w/ 80% gate, dependency scan, Docker build + smoke test |
| Dependency vulnerability scan | ✅ | `pip-audit`: no known vulnerabilities |
| Known issues documented | ✅ | README "Known limitations", `docs/final-engineering-summary.md` |
| Release notes | ✅ | `CHANGELOG.md` |

## Known issues at release

- Deterministic agents use a fixed rule set (ADR-004), not general NLU.
- In-process (thread-based) parallelism, not distributed (ADR-010).
- Replanning operates at artifact-type granularity (documented trade-off).
- MTTR / approval-waiting-time metrics not implemented (stated, not faked).
- No live-LLM mode built out; no workflow-approval REST API (CLI-only by design, ADR-008).

None of these block release — all are prototype-scope decisions made and documented deliberately, not defects.

## Go/no-go

**Recommendation: GO.** All checks above pass with real evidence, not assumption. Pending: your Gate 3 approval (release scope, per `docs/decisions/approvals-log.md`'s pattern).
