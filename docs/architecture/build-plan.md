# Build Plan — Phase 6

**Status:** DRAFT — last step before formal Gate 2 (bundled with Phase 3-5 architecture for approval)
**Input:** architecture-overview.md, ai-dlc-design.md, detailed-technical-design.md, ADR-001…012

---

## 1. Priority Legend

- **P0** — required for a minimally viable, governed, testable prototype (DoD §26 depends on all of it).
- **P1** — required for a *complete* submission (full test depth, docs, failure-injection demo).
- **P2** — nice-to-have; only attempted after every P0/P1 item is done and validated.

## 2. Branch Strategy

| Branch | Scope |
|---|---|
| `feature/greenfield-url-shortener` | P0 core app (tasks 1-8 below) + greenfield scenario runner |
| `feature/agentic-orchestration` | P0 orchestration engine, agents, gates, retry/rollback/replanning, metrics (tasks 9-20) |
| `feature/brownfield-expiry` | SCEN-02's real code change (configurable expiry + refactor + regression fix) + its scenario runner |
| `feature/ambiguous-security` | SCEN-03's real code change (rate limiting — see §4 note) + its scenario runner |
| `feature/docker-ci` | Dockerfile, docker-compose.yml, GitHub Actions |
| `docs/reviewer-package` | README, REVIEWER_GUIDE, AI_USAGE, SECURITY, CHANGELOG, final summary |

Each branch merges to `master` only after its own validation checkpoint passes locally. `master` stays green at every merge — matches §4.4's "small, controlled increments," extending the discipline already used for every doc commit so far.

## 3. Ordered Build Tasks (P0)

| # | Task | Key files | Branch | Depends on | Validation checkpoint |
|---|---|---|---|---|---|
| 1 | Project foundation | `pyproject.toml`, package skeleton, `.gitignore`, `.env.example` | greenfield | — | `pip install -e .` succeeds |
| 2 | Config | `app/config.py` | greenfield | 1 | unit test: env defaults load correctly |
| 3 | Database + migrations | `app/database/`, `app/models/` (short_urls, click_events), Alembic init | greenfield | 2 | `alembic upgrade head` on a fresh DB |
| 4 | Security validation | `app/services/url_safety.py` | greenfield | 2 | `tests/security` green (scheme/SSRF/RNG) |
| 5 | Core URL API | `app/api/urls.py`, `app/api/redirect.py`, `app/schemas/` | greenfield | 3, 4 | integration tests for FR-01/02/03/05/06/07 |
| 6 | Analytics | `app/services/analytics.py` | greenfield | 3 | concurrency test for NFR-09 |
| 7 | Health | `app/api/health.py` | greenfield | 3 | `/health` reflects real DB check |
| 8 | App test consolidation | `tests/unit/`, `tests/integration/` | greenfield | 1-7 | `pytest tests/unit tests/integration` green; `docker compose up --build` serves `/health`, `/docs` |
| 9 | Orchestration data model | migration for workflow_runs/workflow_events/artifacts/approvals | orchestration | 3 | `alembic upgrade head` adds all 4 tables |
| 10 | Agent contract | `agentic/context.py`, `agentic/agents/base.py` | orchestration | 9 | unit test: `AgentResult`/`ValidationResult` schema round-trip |
| 11 | State + graph | `agentic/state.py`, `agentic/graph.py` | orchestration | 10 | unit test: no orphan nodes, every gate ∈ {requirements, architecture, release} |
| 12 | Orchestrator core | `agentic/orchestrator.py` | orchestration | 11 | orchestration test: single-path run reaches a gate and persists state |
| 13 | Policies | `agentic/policies.py` | orchestration | 12 | unit test: denylisted architecture component rejected |
| 14 | 7 agents (deterministic) | `agentic/agents/*.py` | orchestration | 10 | one unit test per agent per §4 of ai-dlc-design.md |
| 15 | Approval | `agentic/approvals.py`, `scripts/approve_gate.py` | orchestration | 12 | orchestration test: gate pause → CLI approve → resume |
| 16 | Artifact store | `agentic/artifact_store.py` | orchestration | 9 | unit test: version increments only on content-hash change; approved version immutable |
| 17 | Retry | `agentic/retry.py` | orchestration | 12 | orchestration test: bounded at 2, correct retry/exhausted decision |
| 18 | Rollback | `agentic/rollback.py` | orchestration | 17 | orchestration test: rollback restores last-approved artifacts + git checkpoint, ends SAFE_STOPPED |
| 19 | Replanning | `agentic/replanning.py` | orchestration | 16 | test using the exact 30-day → 1-365-day case (§13 detailed-technical-design.md), asserting exact stale/preserved sets |
| 20 | Metrics | `agentic/metrics.py`, `scripts/generate_metrics.py` | orchestration | 12 | unit test: seeded `workflow_events` → known expected metric values |

**Checkpoint after task 20:** `pytest tests/orchestration` green — parallel branch+join, all 3 gates (pause/approve/reject), retry, rollback, safe-stop, and replanning all independently demonstrated.

## 4. Ordered Build Tasks (P1)

| # | Task | Key files | Branch | Depends on | Validation checkpoint |
|---|---|---|---|---|---|
| 21 | Greenfield scenario runner | `scripts/run_greenfield.py` | greenfield | 8, 20 | full run reaches COMPLETED (with all 3 gates approved via CLI) |
| 22 | Brownfield code change + runner | `app/config.py` (DEFAULT_EXPIRY_DAYS→range), new migration, extracted `app/services/expiry.py` (the refactor), regression test that catches the seeded boundary bug, `scripts/run_brownfield.py` | brownfield | 21 | full regression suite green + replanning test (task 19) exercised against this real change |
| 23 | Ambiguous scenario + rate limiting | `app/api/middleware/rate_limit.py`, `scripts/run_ambiguous.py` | ambiguous | 21 | ≥5 interpretations surfaced, workflow pauses at Gate 1, only rate limiting is net-new code (scheme/SSRF/secure-RNG are already satisfied by the greenfield build — see note below) |
| 24 | Failure injection | `--inject-failure <stage>`, `--inject-permanent-failure` flags on scenario scripts | orchestration | 17, 18 | demonstrates retry → exhaustion → rollback → safe-stop → blocked release, on demand |
| 25 | Full test depth + traceability | negative tests, security tests, coverage report, requirement-to-test matrix | all | 8, 20-24 | ≥80% coverage; every FR/NFR/ORCH/GOV ID has ≥1 linked test |
| 26 | Docker + CI | `Dockerfile`, `docker-compose.yml`, `.github/workflows/ci.yml` | docker-ci | 25 | cold `docker compose up --build` works; CI config lints locally (`act` not required — structural check only, since no remote to actually trigger it yet) |
| 27 | Reviewer docs | `README.md`, `REVIEWER_GUIDE.md`, `AI_USAGE.md`, `SECURITY.md`, `CHANGELOG.md` | docs/reviewer-package | 26 | five-minute reviewer path actually walked end to end |

**Note on task 23:** the ambiguous scenario's approved interpretation (per requirements-baseline.md SCEN-03: block unsafe schemes, block private-network destinations, secure random codes, add rate limiting, defer auth) mostly restates controls the greenfield build *already has* (NFR-01/02). The only genuinely new code is rate limiting. This is intentional, not a shortcut: the Requirement Analysis Agent's honest output for this scenario is "4 of these 5 are already satisfied by the existing baseline; 1 is net-new" — re-implementing already-existing controls just to look busy would be worse engineering, not better governance.

## 5. Ordered Build Tasks (P2 — only if time remains after P0+P1 fully validated)

| # | Task | Depends on |
|---|---|---|
| 28 | Real `agentic/llm_provider.py` integration (still off by default) | 14 |
| 29 | Optional workflow-approval REST endpoint (ADR-008 currently says skip) | 15 |
| 30 | Final engineering summary + production backlog doc | 27 |

## 6. Commit Strategy

- Conventional prefixes: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `ci` — same discipline already used for every doc commit in this session.
- One logical change per commit; a feature's tests land in the **same** commit as the code they test, not a follow-up "add tests" commit — except task 25's consolidation pass, which is explicitly about *additional* depth beyond what shipped with each feature.
- No commit lands on `master` without its task's validation checkpoint passing first.

## 7. Definition of Done

This build plan is done when every checkpoint above has passed **and**:
- requirements-baseline.md §18 acceptance criteria are all met.
- Every ID in the §0 traceability matrix (FR/NFR/ORCH/GOV/TRACE/METRIC/SCEN/SUBMIT) has a task above that builds it and a checkpoint that verifies it — cross-checked, not assumed.
- `docker compose up --build` → `/health`, `/docs`, `/openapi.json` all reachable, on a clean checkout, with no manual steps and no API key.

---
*Produced by: Planning Agent (deterministic mode) — Phase 6 of the SDLC Orchestrator. This document, together with Phases 3-5, forms the Gate 2 approval bundle.*
