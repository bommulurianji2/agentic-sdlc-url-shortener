# ADR-003: Single SQLite file for both application and orchestration tables

**Status:** Accepted

**Context:** `short_urls`/`click_events` (application data) and `workflow_runs`/`workflow_events`/`artifacts`/`approvals` (orchestration data) are logically distinct, but both need persistence, and the prototype uses SQLite by default (binding assumption).

**Decision:** One SQLite file, one Alembic migration chain, both table groups in the same schema.

**Alternatives considered:**
- Two separate SQLite files/connections — cleaner separation of concerns, but doubles the Docker volume/migration setup for no reviewer-visible benefit at this scale, and complicates any query that needs to join across the two (e.g. showing a `short_urls` row's `creating_workflow_id`).

**Consequences:** Simplicity now; a documented production risk (§10 of architecture-overview.md — lock contention between app traffic and scenario runs under concurrent load) and an explicit production-evolution backlog item to split them (e.g. app on Postgres, orchestration state in a separate store) if this ever needed to scale.
