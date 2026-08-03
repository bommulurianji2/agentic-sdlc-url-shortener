# Detailed Technical Design — Phase 5

**Status:** DRAFT — feeds into Gate 2 (formal, after Phase 6)
**Input:** requirements-baseline.md v3, architecture-overview.md, ai-dlc-design.md, ADR-001…012

This phase fixes every remaining exact value (column types, error codes, formulas, algorithms) so Phase 7 implementation has zero open questions to improvise on.

---

## 1. Data Model

### `short_urls`

| Column | Type | Constraint |
|---|---|---|
| id | INTEGER | PK, autoincrement |
| short_code | VARCHAR(32) | UNIQUE NOT NULL, indexed |
| original_url | TEXT | NOT NULL |
| created_at | DATETIME | NOT NULL |
| expires_at | DATETIME | NULL |
| status | VARCHAR(16) | NOT NULL DEFAULT 'active' — enum `active`\|`disabled` |
| click_count | INTEGER | NOT NULL DEFAULT 0 |
| last_accessed_at | DATETIME | NULL |
| version | INTEGER | NOT NULL DEFAULT 1 (optimistic concurrency on status/expiry updates) |
| creating_workflow_id | VARCHAR(36) | NULL, FK → `workflow_runs.id` |

**Two decisions worth stating explicitly, not left implicit:**

1. **"Expired" is a derived condition, not a stored status.** `status` only ever holds `active`/`disabled`. A link is effectively expired when `expires_at IS NOT NULL AND expires_at < now()` — computed at read/redirect time. Storing a third `expired` status would need a background job to flip it at the right moment, which is unjustified complexity (and a race condition source) for a value trivially computed on read. FR-05's "expired links remain visible via the info API" works either way, but computing it avoids a whole class of staleness bugs.
2. **`creating_workflow_id` is populated only when a `short_urls` row is created by a scenario-runner script as demonstration evidence** (e.g. the greenfield scenario creating a sample link to prove FR-01/02 end-to-end). Ordinary API traffic from a real client has no associated SDLC workflow run, so this column is `NULL` for it. This is what the master brief's data model section literally asks for (a per-URL link back to the workflow that created it) — most URLs simply won't have one, and that's correct, not a bug.

### `click_events`

| Column | Type | Constraint |
|---|---|---|
| id | INTEGER | PK, autoincrement |
| short_url_id | INTEGER | NOT NULL, FK → `short_urls.id` |
| accessed_at | DATETIME | NOT NULL |
| referrer_domain | VARCHAR(255) | NULL |
| user_agent_category | VARCHAR(16) | NULL — enum `browser`\|`bot`\|`other` |
| correlation_id | VARCHAR(36) | NOT NULL |

### `workflow_runs`

| Column | Type | Constraint |
|---|---|---|
| id | VARCHAR(36) | PK (UUID) |
| scenario_type | VARCHAR(16) | NOT NULL — enum `greenfield`\|`brownfield`\|`ambiguous` |
| status | VARCHAR(32) | NOT NULL — §10 state enum (coarse) |
| current_stage | VARCHAR(32) | NOT NULL — §9 graph node (fine) — see architecture-overview.md §4.1 mapping |
| started_at | DATETIME | NOT NULL |
| completed_at | DATETIME | NULL |
| retry_count | INTEGER | NOT NULL DEFAULT 0 |
| rollback_count | INTEGER | NOT NULL DEFAULT 0 |
| failure_count | INTEGER | NOT NULL DEFAULT 0 |
| revision | INTEGER | NOT NULL DEFAULT 1 — incremented on each replanning pass |

### `workflow_events`

| Column | Type | Constraint |
|---|---|---|
| id | VARCHAR(36) | PK (UUID) |
| workflow_id | VARCHAR(36) | NOT NULL, FK |
| agent | VARCHAR(64) | NULL (NULL for orchestrator-level events, e.g. gate/rollback) |
| stage | VARCHAR(32) | NOT NULL |
| event_type | VARCHAR(32) | NOT NULL — enum: `stage_start`\|`stage_success`\|`stage_failure`\|`retry`\|`rollback`\|`gate_pending`\|`gate_approved`\|`gate_rejected`\|`replan`\|`safe_stop` |
| input_artifact_ids | TEXT | NULL, JSON array |
| output_artifact_ids | TEXT | NULL, JSON array |
| decision | TEXT | NULL |
| reason | TEXT | NULL |
| timestamp | DATETIME | NOT NULL |
| duration_ms | INTEGER | NULL |
| error_details | TEXT | NULL |
| correlation_id | VARCHAR(36) | NOT NULL |

### `artifacts`

| Column | Type | Constraint |
|---|---|---|
| id | VARCHAR(36) | PK (UUID) |
| workflow_id | VARCHAR(36) | NOT NULL, FK |
| artifact_type | VARCHAR(32) | NOT NULL — enum `requirement`\|`plan`\|`architecture`\|`development`\|`test`\|`security_review`\|`release` |
| version | INTEGER | NOT NULL, starts at 1 |
| status | VARCHAR(16) | NOT NULL — enum `draft`\|`approved`\|`stale`\|`superseded` |
| content_path | VARCHAR(255) | NOT NULL |
| checksum | VARCHAR(64) | NOT NULL — sha256 hex digest |
| created_by | VARCHAR(64) | NOT NULL — agent name |
| created_at | DATETIME | NOT NULL |

### `approvals`

| Column | Type | Constraint |
|---|---|---|
| id | VARCHAR(36) | PK (UUID) |
| workflow_id | VARCHAR(36) | NOT NULL, FK |
| gate | VARCHAR(32) | NOT NULL — enum `requirements`\|`architecture`\|`release` |
| approver | VARCHAR(128) | NOT NULL |
| decision | VARCHAR(16) | NOT NULL — enum `approved`\|`rejected` |
| comments | TEXT | NULL |
| artifact_versions | TEXT | NOT NULL — JSON `{artifact_type: version}` |
| timestamp | DATETIME | NOT NULL |

## 2. API Contracts

### `POST /api/v1/urls` → 201

```
Request:  { original_url: str (≤2048 chars, required),
            custom_alias: str | null (3-32 chars, [a-zA-Z0-9_-], not reserved),
            expires_at: datetime | null,
            expires_in_days: int | null (1-365) }   # brownfield addition, see note below
Response: { short_code, short_url, original_url, created_at, expires_at, status }
```

**Expiry semantics — the exact greenfield/brownfield split, pinned down here because it's the same change the master brief uses as its dynamic-replanning worked example (§13: "expires after 30 days" → "configurable between 1 and 365 days"), and it deliberately doubles as SCEN-02's core change and the ORCH-10 replanning demonstration — one real change, two things it proves, not two separate changes invented to satisfy two requirement IDs separately:**

- **Greenfield (v1.0.0):** `expires_at` accepted as-is if provided (no range validation); if omitted, defaults to `created_at + 30 days`, fixed. No `expires_in_days` field exists yet.
- **Brownfield (v1.1.0):** adds `expires_in_days` (1-365); if provided, `expires_at = created_at + expires_in_days`. If a raw `expires_at` is provided instead, it's now validated to fall within 1-365 days of `created_at` (previously unvalidated). Omitting both still defaults to 30 days, but the constant becomes a named, configurable default rather than a hardcoded literal — which is exactly the refactor named in SCEN-02.

### `GET /{short_code}` → 307 | error

Redirects if `status == active` and not expired (§1 derived rule); else a structured error (`URL_EXPIRED`, `URL_DISABLED`, or `UNKNOWN_SHORT_CODE`).

### `GET /api/v1/urls/{short_code}` → 200 | 404

```
Response: { short_code, original_url, created_at, expires_at, status, click_count, last_accessed_at }
```

### `GET /api/v1/urls/{short_code}/analytics` → 200 | 404

```
Response: { short_code, total_clicks, created_at, last_accessed_at,
            click_events: [{ accessed_at, referrer_domain, user_agent_category }] }
```

### `PATCH /api/v1/urls/{short_code}` → 200 | 404 | 409

```
Request:  { status: "disabled" | "active" }
Response: same shape as GET .../urls/{short_code}
```
409 (`WORKFLOW_CONFLICT`... actually here it's a plain optimistic-concurrency conflict) if the record's `version` changed between read and write — caller retries.

### `GET /health` → 200

```
Response: { status: "ok"|"degraded", database: "connected"|"error", execution_mode: "deterministic"|"llm", version: "<app version>" }
```
`database` reflects a real `SELECT 1` against the SQLite connection (NFR-09) — not hardcoded.

## 3. Error Model

Single envelope (master brief §16):
```json
{ "error": { "code": "...", "message": "...", "correlation_id": "...", "details": null } }
```

| Code | HTTP | Meaning |
|---|---|---|
| `INVALID_URL` | 422 | malformed URL |
| `UNSAFE_SCHEME` | 422 | scheme not in `{http, https}` |
| `BLOCKED_PRIVATE_DESTINATION` | 422 | resolves to loopback/private/link-local/metadata address |
| `UNKNOWN_SHORT_CODE` | 404 | no such code |
| `URL_EXPIRED` | 410 | past `expires_at` |
| `URL_DISABLED` | 410 | `status == disabled` |
| `DUPLICATE_ALIAS` | 409 | custom alias already in use |
| `VALIDATION_FAILURE` | 422 | generic schema validation error |
| `APPROVAL_REQUIRED` | 409 | orchestration: action needs a pending gate resolved first |
| `WORKFLOW_CONFLICT` | 409 | orchestration: optimistic-concurrency/version conflict |
| `RETRY_EXHAUSTED` | 409 | orchestration: bounded retries used up |
| `SAFE_STOP` | 409 | orchestration: workflow is safe-stopped, cannot proceed |
| `INTERNAL_ERROR` | 500 | unhandled — message is generic, real detail goes only to server-side logs keyed by `correlation_id` |

## 4. Workflow State Model — Transition Table

Extends architecture-overview.md §4.1 (status↔stage mapping) with the actual allowed transitions:

| From status | Event | To status |
|---|---|---|
| CREATED | analysis starts | ANALYSING |
| ANALYSING | analysis complete | WAITING_FOR_REQUIREMENT_APPROVAL |
| WAITING_FOR_REQUIREMENT_APPROVAL | approved | PLANNED |
| WAITING_FOR_REQUIREMENT_APPROVAL | rejected | REJECTED |
| PLANNED | architecture starts | DESIGNING |
| DESIGNING | architecture complete | WAITING_FOR_ARCHITECTURE_APPROVAL |
| WAITING_FOR_ARCHITECTURE_APPROVAL | approved | IMPLEMENTING |
| WAITING_FOR_ARCHITECTURE_APPROVAL | rejected | REJECTED |
| IMPLEMENTING | join reached, tests run | TESTING |
| TESTING | pass | REVIEWING |
| TESTING | fail, retries remain | RETRYING |
| TESTING | fail, retries exhausted | ROLLING_BACK |
| REVIEWING | pass | WAITING_FOR_RELEASE_APPROVAL |
| REVIEWING | critical finding | SAFE_STOPPED |
| REVIEWING | non-critical finding, retries remain | RETRYING |
| RETRYING | corrected | IMPLEMENTING |
| RETRYING | retries exhausted | ROLLING_BACK |
| ROLLING_BACK | restored | SAFE_STOPPED |
| WAITING_FOR_RELEASE_APPROVAL | approved | RELEASE_READY |
| WAITING_FOR_RELEASE_APPROVAL | rejected | REJECTED |
| RELEASE_READY | finalized | COMPLETED |
| any active state | upstream artifact changes | REPLANNING |
| REPLANNING | stale nodes re-executed | *(returns to the coarse status of the first stale node)* |

`SAFE_STOPPED`, `REJECTED`, `COMPLETED` are terminal. Only `COMPLETED` may be tagged/released (enforced by a single guard function `can_release(run) -> bool`, not scattered checks).

## 5. Dependency Graph (as implemented in `agentic/graph.py`)

```python
NODES = {
  "REQUIREMENT_ANALYSIS":     {"agent": "requirement_analysis", "next": ["REQUIREMENT_VALIDATION"]},
  "REQUIREMENT_VALIDATION":   {"agent": None, "next": ["HUMAN_GATE_REQUIREMENTS"]},
  "HUMAN_GATE_REQUIREMENTS":  {"agent": None, "gate": "requirements", "next": ["TASK_DECOMPOSITION"]},
  "TASK_DECOMPOSITION":       {"agent": "planning", "next": ["ARCHITECTURE_DESIGN"]},
  "ARCHITECTURE_DESIGN":      {"agent": "architecture", "next": ["ARCHITECTURE_VALIDATION"]},
  "ARCHITECTURE_VALIDATION":  {"agent": None, "next": ["HUMAN_GATE_ARCHITECTURE"]},
  "HUMAN_GATE_ARCHITECTURE":  {"agent": None, "gate": "architecture", "next": ["IMPLEMENTATION", "TEST_DESIGN"]},  # fan-out
  "IMPLEMENTATION":           {"agent": "development", "next": ["JOIN"]},
  "TEST_DESIGN":               {"agent": "test", "next": ["JOIN"]},
  "JOIN":                       {"agent": None, "join_of": ["IMPLEMENTATION", "TEST_DESIGN"], "next": ["TEST_EXECUTION"]},
  "TEST_EXECUTION":             {"agent": "test", "next": {"pass": "SECURITY_REVIEW", "fail": "RETRY_EVALUATION"}},
  "SECURITY_REVIEW":            {"agent": "security_review",
                                  "next": {"pass": "DOCUMENTATION", "non_critical": "RETRY_EVALUATION", "critical": "SAFE_STOP"}},  # ADR-007 fix
  "RETRY_EVALUATION":            {"agent": None, "next": {"retry": "IMPLEMENTATION", "exhausted": "ROLLBACK"}},
  "ROLLBACK":                     {"agent": None, "next": ["SAFE_STOP"]},
  "SAFE_STOP":                    {"agent": None, "terminal": True},
  "DOCUMENTATION":                {"agent": "documentation_release", "next": ["RELEASE_READINESS"]},
  "RELEASE_READINESS":            {"agent": "documentation_release", "next": ["HUMAN_GATE_RELEASE"]},
  "HUMAN_GATE_RELEASE":            {"agent": None, "gate": "release", "next": ["COMPLETE"]},
  "COMPLETE":                       {"agent": None, "terminal": True},
}
```

`orchestrator.py` walks this dict; `tests/orchestration` asserts on it directly (no orphan nodes, every non-terminal node has a `next`, every `gate` value is one of the three defined gates).

## 6. Security Controls (exact logic)

```python
ALLOWED_SCHEMES = {"http", "https"}

def is_blocked_host(hostname: str) -> bool:
    ip = resolve_to_ip(hostname)  # via socket.getaddrinfo
    addr = ipaddress.ip_address(ip)
    return (
        addr.is_loopback or addr.is_private or addr.is_link_local or
        addr.is_reserved or str(addr) in CLOUD_METADATA_IPS  # {"169.254.169.254", "fd00:ec2::254", ...}
    )

def generate_short_code(length: int = 7) -> str:
    return secrets.token_urlsafe(length)[:length]  # cryptographically secure, NFR-02
```
Full DNS-rebinding protection (re-resolving at request time, pinning resolved IPs) is explicitly **not** implemented — documented as a production-only enhancement (requirements-baseline.md §5 Out of Scope), since the resolved-at-creation-time check is what NFR-01 actually asks for.

## 7. Configuration Plan

| Env var | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `sqlite:////data/app.db` | SQLAlchemy connection string |
| `AGENT_MODE` | `deterministic` | `deterministic`\|`llm` |
| `LLM_API_KEY` | *(unset)* | only read if `AGENT_MODE=llm`; never required otherwise |
| `LOG_LEVEL` | `INFO` | stdlib logging level |
| `APP_VERSION` | read from `pyproject.toml` | surfaced at `/health` |
| `SHORT_CODE_LENGTH` | `7` | short-code length |
| `DEFAULT_EXPIRY_DAYS` | `30` | see §2 expiry semantics |

`.env.example` lists all of these with the same defaults; `.env` is gitignored.

## 8. Logging Schema (structured JSON, one object per line, to stdout)

```json
{"timestamp": "...", "level": "INFO", "correlation_id": "...", "logger": "app.api.urls",
 "message": "...", "workflow_id": null, "extra": {}}
```
`workflow_id` populated only for orchestration-originated log lines. No field ever holds a secret value — logging config is itself one of the Security & Quality Review Agent's checklist items (§4.6 of ai-dlc-design.md).

## 9. Metrics Formulas (METRIC-01)

| Metric | Formula |
|---|---|
| Success rate | `COMPLETED runs / total terminal runs` (terminal = COMPLETED ∪ REJECTED ∪ SAFE_STOPPED ∪ FAILED) |
| Retry frequency | `SUM(retry_count) / COUNT(workflow_runs)` |
| Rollback frequency | `SUM(rollback_count) / COUNT(workflow_runs)` |
| MTTR | `AVG(time from first stage_failure event to the next stage_success event for the same stage, per run)` |
| End-to-end latency | `completed_at - started_at` per run |
| Agent-step latency | `AVG(duration_ms)` per `agent` from `workflow_events` |
| Approval waiting time | `gate_approved.timestamp - gate_pending.timestamp` per gate |
| Failed-stage frequency | `COUNT(stage_failure) GROUP BY stage` |
| Artifact first-pass acceptance rate | `COUNT(artifacts WHERE version = 1 AND status = 'approved') / COUNT(artifacts WHERE version = 1)` |
| Replanning count | `COUNT(event_type = 'replan')` |
| Stale artifacts regenerated | `COUNT(artifacts WHERE status transitioned stale → new version)` per replan |
| Unaffected artifacts preserved | `COUNT(artifacts WHERE status remained 'approved') ` per replan |

## 10. Artifact Versioning

`version = 1` on first write. On a **material** change (content hash differs from the current approved version), a new row is written with `version = previous + 1`, `status = 'draft'`; the prior row's `status` becomes `superseded` only once the new version is *approved* — so a rejected draft never displaces an approved version (GOV-07 as code, not convention). `checksum = sha256(content)`, checked on every read as an integrity guard.

## 11. Retry Semantics

```python
MAX_RETRIES = 2

def evaluate_retry(run, failure) -> Literal["retry", "exhausted"]:
    if not failure.retryable or run.retry_count >= MAX_RETRIES:
        return "exhausted"
    run.retry_count += 1
    log_event(run, "retry", reason=failure.reason, attempt=run.retry_count)
    return "retry"
```
A retry always re-invokes the *same* failing agent with the same context plus the recorded failure reason appended — never silently retried with no record of what changed.

## 12. Rollback Semantics

```python
def rollback(run):
    last_approved = get_last_approved_artifacts(run)     # per artifact_type
    restore_artifacts(run, last_approved)                 # supersede any draft/stale versions
    restore_git_checkpoint(run.last_approved_commit)       # git reset to the last approved commit for this run's branch
    run.rollback_count += 1
    run.status = "SAFE_STOPPED"
    log_event(run, "rollback", reason="retry_exhausted")
```
Rollback always ends in `SAFE_STOPPED` (GOV-04) — it never silently returns the run to an active state; re-entry requires a human decision (re-approve or replan), not an automatic resume.

## 13. Replanning Algorithm (ORCH-10)

```python
def replan(run, changed_requirement):
    old_ids = set(run.approved_requirement.all_ids())
    new_ids = set(changed_requirement.all_ids())
    changed = (old_ids ^ new_ids) | modified_ids(old_ids & new_ids, run.approved_requirement, changed_requirement)
    stale = set()
    for artifact_type, artifact in run.artifacts_by_type().items():
        if artifact.depends_on_any(changed):
            stale.add(artifact_type)
    preserved = set(run.artifacts_by_type()) - stale
    for artifact_type in topological_order(stale, GRAPH_DEPENDS_ON):
        re_invoke_agent_for(artifact_type, run)   # only these agents re-run
    run.revision += 1
    log_event(run, "replan", reason=f"changed={changed}", details={"stale": list(stale), "preserved": list(preserved)})
```
**Concrete worked demonstration (also SCEN-02, §2 above):** requirement changes from "expires after 30 days" (fixed) to "configurable 1-365 days." Expected `stale = {requirement, architecture(data model + create-API section), development(expiry logic + migration), test(expiry tests), documentation}`; expected `preserved = {architecture(security section), development(short-code generation, health endpoint, redirect routing)}` — matching the master brief's own worked example exactly (§13).

## 14. Coding Standards

- Line length 100 (ruff/black default-compatible), Python 3.12, type hints on every public function signature.
- Pydantic v2 models for every API and agent I/O boundary — no untyped dicts crossing a module boundary.
- No comments explaining *what* code does; a comment is only added for a non-obvious *why* (matches this session's own established practice).
- No bare `except:` — always a specific exception type; unhandled exceptions bubble to a single FastAPI exception handler that maps to `INTERNAL_ERROR`.

## 15. Naming Conventions

- Files/modules: `snake_case.py`. Classes: `PascalCase`. Functions/variables: `snake_case`.
- DB tables: plural `snake_case` (already fixed by the master brief — `short_urls`, `click_events`, etc.).
- Error codes: `SCREAMING_SNAKE_CASE` (§3 above).
- Requirement IDs (already established): `FR-`, `NFR-`, `ORCH-`, `GOV-`, `TRACE-`, `METRIC-`, `SCEN-`, `SUBMIT-`, `ADR-`, each zero-padded two digits.
- Agent module files: `agentic/agents/<role>_agent.py` (e.g. `requirement_analysis_agent.py`).

---
*Produced by: Architecture Agent (deterministic mode) — Phase 5 of the SDLC Orchestrator.*
