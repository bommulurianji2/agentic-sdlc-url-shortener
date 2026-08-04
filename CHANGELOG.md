# Changelog

## v1.2.0-final-assessment (unreleased)

- Docker + GitHub Actions CI (lint, type-check, tests with coverage gate, dependency scan, image build + smoke test).
- Full test-depth pass: closed coverage gaps in `agentic/metrics.py` (0% → 100%), `app/services/analytics.py`, `app/api/health.py`, `agentic/artifact_store.py`. 117 tests, 96% overall coverage.
- Requirement-to-test traceability matrix (`docs/testing/traceability-matrix.md`).
- Reviewer documentation: README, REVIEWER_GUIDE, SECURITY, AI_USAGE (this changelog's sibling docs).

## v1.1.0-brownfield

- **Enhancement**: configurable link expiry (`expires_in_days`, 1–365 days), replacing the fixed 30-day-only default.
- **Refactor**: extracted expiry computation out of the route handler into `app/services/expiry.py`.
- **Migration**: additive, nullable `short_urls.disabled_at`, stamped on disable and cleared on reactivation — fully backward compatible, existing rows unaffected.
- **Bug fix**: a regression test caught `expires_in_days` accepting 0, negative, or >365 values unchecked; fixed under change control before the buggy version was ever committed (see `docs/architecture/detailed-technical-design.md` #2 and the commit history for `app/services/expiry.py`).
- Dynamic replanning demonstrated live: the same expiry change is the master brief's own worked example (30-day fixed → 1–365-day configurable) — `scripts/run_brownfield.py` prints the changed requirement ID and the resulting stale/preserved artifact sets.
- `scripts/run_brownfield.py` scenario runner.

## v1.0.0-greenfield

- Initial URL shortener: create, redirect, retrieve details, retrieve analytics, expiry, disable, custom alias, health check (FR-01–FR-08).
- Security: URL scheme allowlist + SSRF/private-network blocking, cryptographically secure short codes, privacy-conscious analytics (NFR-01–NFR-09).
- Full governed agentic orchestration engine: dependency graph, 7 deterministic agents, 3 human approval gates, bounded retry, rollback, safe-stop, dependency-aware replanning, prototype reliability metrics.
- `scripts/run_greenfield.py`, `scripts/approve_gate.py`, `scripts/run_demo.py`.
- Ambiguous-requirement scenario ("make shortened links more secure"): 8 candidate interpretations analyzed, workflow paused for real clarification, approved interpretation (rate limiting — the one net-new control beyond the existing baseline) implemented via `scripts/run_ambiguous.py`.
- 12 architecture decision records (`docs/decisions/`), including two corrections to gaps found in the master brief's own specification (the `SECURITY_REVIEW` fail-path, and Gate 2's timing relative to the build plan).
