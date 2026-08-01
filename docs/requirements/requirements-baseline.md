# Requirements Baseline — Greenfield Scenario

**Status:** DRAFT — awaiting Human Gate 1 (Requirement Approval)
**Scenario:** Greenfield
**Source requirement (as submitted):**
> Build a URL-shortener service that creates short URLs, redirects users, records privacy-conscious analytics, and handles invalid input safely.

---

## 1. Business Objective

Provide a working URL-shortener service, and — as the primary deliverable of this assessment — demonstrate that requirement can be taken through a governed, auditable, agent-assisted software delivery process: interpreted, decomposed, designed, implemented, tested, reviewed, and released with human accountability preserved at every material decision point.

## 2. Problem Statement

Users need a way to turn long URLs into short, shareable links, have those links reliably redirect to the original destination, and see basic, privacy-respecting usage analytics — without the service becoming a vector for abuse (malicious redirect targets, internal-network probing, enumeration, etc.).

## 3. Actors

| Actor | Description |
|---|---|
| **API Consumer** | Any client (script, browser, tool) calling the REST API to create/inspect/manage short URLs. |
| **End User (link clicker)** | Anyone who follows a short link and is redirected to the original URL. |
| **Reviewer / Operator** | Person running the service locally (Docker), exercising the API via Swagger, and acting as the human approver at workflow gates. |
| **Orchestrator/Agents** | Internal system actors that analyze, plan, design, implement, test, and review — never customer-facing, always subject to the controls in §12 of the master brief. |

## 4. Scope

In scope for the greenfield build:

- Create a short URL from a valid long URL, with optional custom alias and optional expiry.
- Redirect from a short code to its original URL.
- Retrieve metadata for a short URL (status, timestamps, click count).
- Retrieve privacy-conscious analytics for a short URL.
- Enforce URL safety controls at creation time (scheme allowlist, SSRF/private-network blocking).
- Health/readiness endpoint and OpenAPI documentation.
- Persist data in SQLite via SQLAlchemy, with Alembic migrations.
- Deterministic, offline-capable execution — no API key required to run or evaluate.

## 5. Out of Scope (Greenfield)

Explicitly deferred, per binding assumption §3.19 and the "do not overengineer" list (§4):

- User accounts, authentication, authorization, or link ownership.
- Rate limiting (introduced later only if the ambiguous-security scenario selects it).
- Hard delete of links (only status changes / disabling).
- Custom frontend UI (Swagger is the UI).
- Any cloud/production infrastructure (Kubernetes, multi-region, service mesh, etc.).
- Full DNS-rebinding protection (documented as a production enhancement, not implemented).
- Live LLM execution as a requirement (optional, never required for reviewer execution).

## 6. Functional Requirements

| ID | Requirement | Notes |
|---|---|---|
| FR-01 | Create a short URL: `POST /api/v1/urls` accepting original URL, optional custom alias, optional expiry; returns short code, short URL, original URL, created/expiry timestamps, status. | |
| FR-02 | Redirect: `GET /{short_code}` resolves an active code, records an analytics event, and issues a redirect; returns a controlled error for unknown/disabled/expired codes. | Uses HTTP 307 (temporary redirect) — see NFR rationale below. |
| FR-03 | Retrieve URL details: `GET /api/v1/urls/{short_code}` returns original URL, code, timestamps, status, click count, last-accessed time. | |
| FR-04 | Retrieve analytics: `GET /api/v1/urls/{short_code}/analytics` returns total clicks, created/last-accessed timestamps, click-event timestamps, optional referrer domain, optional broad user-agent category. No IP address or precise geolocation is ever collected. | |
| FR-05 | Expiry: configurable expiry; expired links do not redirect (controlled error) but remain visible via the info API. | |
| FR-06 | Disable a link: `PATCH /api/v1/urls/{short_code}` supports controlled status transitions (e.g. active → disabled). Hard delete is not implemented in this scenario. | |
| FR-07 | Custom alias: validated for allowed characters, reserved names, max length, and uniqueness. | |
| FR-08 | Health check: `GET /health` reports application status, database status, execution mode, version. | |

## 7. Non-Functional Requirements

| ID | Requirement |
|---|---|
| NFR-01 | **Security:** URL scheme allowlist (`http`/`https` only); SSRF protections blocking localhost, loopback, private IPv4/IPv6, link-local, and common cloud-metadata addresses at creation time. |
| NFR-02 | **Security:** Short codes generated with a cryptographically secure RNG (`secrets` module), not a predictable counter or weak PRNG. |
| NFR-03 | **Privacy:** Analytics never store IP address or precise geolocation. |
| NFR-04 | **Reliability:** Structured, stable error codes and correlation IDs on every error response; no stack traces exposed to API consumers. |
| NFR-05 | **Observability:** Structured JSON logs; every workflow-relevant event is persisted, not just printed. |
| NFR-06 | **Portability:** Runs fully via `docker compose up --build` with no external network dependency and no required API key. |
| NFR-07 | **Testability:** Automated unit, integration, and negative tests exist for every functional requirement above; target ≥80% coverage as a signal, not a sole quality gate. |
| NFR-08 | **Auditability:** Every material engineering decision in the agentic workflow is logged with input/output artifacts, decision, and reason (workflow_events). |

## 8. Constraints

- Python 3.12, FastAPI, Uvicorn, SQLAlchemy, SQLite (default), Alembic, Pytest, Docker/Compose — per binding assumptions.
- Deterministic agent execution must fully cover reviewer needs without any LLM API key.
- No external company-specific compliance standard is invoked; controls are labeled as general secure-engineering practice.
- Repository will be public — no confidential material, secrets, or proprietary content may ever be committed.

## 9. Dependencies

- None on external paid services. Optional live-LLM mode (future/nice-to-have) would depend on an external provider API key, but is never required.

## 10. Assumptions (carried from binding assumptions, restated where relevant to this baseline)

- A01 — SQLite is sufficient for the prototype; a production evolution path (e.g. Postgres) will be documented, not implemented.
- A02 — "Temporary redirect" (FR-02) means HTTP 307, which preserves method semantics and clearly signals to clients/tools that the mapping is not meant to be permanently cached — appropriate for a link whose target can be disabled/expired.
- A03 — "Broad user-agent category" means a coarse classification (e.g. `browser` / `bot` / `other`), not the raw User-Agent string, to stay privacy-conscious.
- A04 — Reserved short-code names (for FR-07 alias validation) include at minimum the API prefix (`api`, `health`, `docs`, `openapi.json`, `redoc`) to avoid alias/route collisions.
- A05 — "Version" in the data model and health endpoint refers to the application/release version, distinct from the per-record optimistic-concurrency `version` field on `short_urls`.

## 11. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Scope is large relative to time available | Incomplete evidence at deadline | Build in priority order (P0 app → P0 orchestration core → scenarios → docs); prioritize completeness of evidence per binding assumption #1 |
| SSRF allowlist/denylist logic is easy to get subtly wrong | Security control gap | Dedicated unit + negative test suite (`tests/security`) before it's marked done |
| Public repo exposure | Leaking secrets/internal material | `.gitignore` from the start; explicit secret scan before any push; nothing pushed until Phase 9 gate |

## 12. Acceptance Criteria (Greenfield)

- All FR-01–FR-08 implemented and covered by automated tests (unit + integration + negative).
- NFR-01–NFR-03 verified by dedicated security tests (invalid scheme, localhost, private IP, weak-RNG check).
- `docker compose up --build` starts the service with no manual steps and no API key.
- `/health`, `/docs`, `/openapi.json` reachable and correct.
- Data persists across a container restart (volume-backed SQLite).
- Requirements baseline (this document) approved at Human Gate 1 before architecture work proceeds.

---
*Produced by: Requirement Analysis Agent (deterministic mode) — Phase 1 of the SDLC Orchestrator.*
