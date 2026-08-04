# Security

The controls below are **general secure-engineering practice** applied at prototype scale — not certification against any named external compliance standard, and not a claim of production-grade infrastructure hardening. See `docs/architecture/architecture-overview.md` §6 for the full architectural rationale.

## URL validation and SSRF protection

Enforced once, at creation time, in `app/services/url_safety.py`:

- **Scheme allowlist**: only `http`/`https`. `javascript:`, `file:`, `data:`, `ftp:`, `gopher:`, and anything else is rejected (`UNSAFE_SCHEME`).
- **SSRF/private-network blocking**: the destination hostname is resolved and rejected if it's loopback, private (RFC 1918), link-local, reserved, multicast, or a known cloud-metadata address (`169.254.169.254`, `metadata.google.internal`, the AWS IMDSv2 IPv6 address) — `BLOCKED_PRIVATE_DESTINATION`.
- **Not implemented, by design**: full DNS-rebinding protection (re-resolving and pinning IPs at redirect time). The destination is validated once at creation; redirects don't re-check DNS on every click. This is a real, stated production gap, not an oversight — see `docs/requirements/requirements-baseline.md` §5 (Out of Scope).

23 dedicated tests: `tests/security/test_url_safety.py`.

## Short-code generation

Cryptographically secure (`secrets.token_urlsafe`), never a predictable counter or a weak PRNG. `tests/security/test_url_safety.py::test_short_code_generation_is_not_deterministic`.

## Rate limiting

A basic sliding-window limiter (`app/api/middleware/rate_limit.py`) on `POST /api/v1/urls` only — 100 requests/minute/IP by default, configurable via `RATE_LIMIT_PER_MINUTE`. This was the one net-new control added for the ambiguous-requirement scenario ("make shortened links more secure") after weighing 8 candidate interpretations — see `docs/requirements/requirements-baseline.md` SCEN-03.

## Privacy

Analytics never store IP address or precise geolocation. Referrer is reduced to domain only (not the full URL, which could carry query strings); User-Agent is reduced to a coarse category (`browser`/`bot`/`other`), never the raw string. `app/services/analytics.py`, `tests/unit/test_analytics.py`.

## Error handling

Every error response uses one structured envelope (`code`/`message`/`correlation_id`/`details`) — no stack trace or raw exception text ever reaches the client. The real exception is logged server-side only, keyed by the same correlation ID. `app/errors.py`, `app/main.py`'s exception handlers.

## Secrets

- Configuration via environment variables only (`app/config.py`); `.env.example` lists every variable with safe defaults, `.env` itself is gitignored.
- No secret, credential, or `.env` value is ever interpolated into an agent prompt, logged, or persisted into an artifact.
- Nothing in this repository requires a live API key to run, test, or evaluate.

## Agent controls

In the deterministic mode this repository runs by default, agents (`agentic/agents/*.py`) are plain Python functions: no shell access, no network access beyond what their own logic explicitly does (e.g. running `pytest`/`ruff` as subprocesses for real test/lint execution), no filesystem writes outside `agentic/artifact_store.py`, and no deployment capability of any kind. The prohibitions in the master brief (agents can't deploy to production, can't bypass approval gates, can't promote a failed artifact, can't take destructive action without approval) hold **by construction** here — there's no capability to misuse, not a runtime policy check hoping to catch a misuse after the fact.

This is stated explicitly, not assumed silently, because it has one real limitation: if the optional live-LLM mode (`agentic/llm_provider.py`, not built out) is ever enabled, an LLM-driven agent *could* attempt to request an action beyond this scope, and that mode would need its own real tool-allowlist enforcement at that point — see [ADR-011](docs/decisions/ADR-011-agent-tool-allowlisting.md).

Governance guardrails that are automated, not just conventions: `agentic/policies.py` rejects any architecture output referencing a denylisted component (Kubernetes, service mesh, event streaming, vector DB/RAG, etc.) and flags any test that gets silently skipped to force a pass. `tests/unit/test_policies.py`.

## Dependency scanning

`pip-audit` runs in CI (informational — flags upstream CVEs without blocking the build, since a transitive advisory shouldn't silently gate every commit). Local: `pip-audit --skip-editable`.

## Responsible disclosure

This is an assessment prototype, not a production service handling real user data. If you find a security issue in the approach or the code, please open a GitHub issue describing it — there's no bug bounty or dedicated security contact, this is not a production system.
