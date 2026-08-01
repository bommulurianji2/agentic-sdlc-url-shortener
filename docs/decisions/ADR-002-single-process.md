# ADR-002: Single process/container hosts both the API and the orchestrator

**Status:** Accepted

**Context:** The application (FastAPI) and the agentic orchestrator are conceptually separate layers. They could be split into separate services (e.g. an API container + a worker container).

**Decision:** Both live in one Python process/container. The API serves reviewer HTTP traffic; the orchestrator is invoked via CLI scripts (`scripts/run_greenfield.py`, etc.), run inside the same container via `docker compose exec api ...`.

**Alternatives considered:**
- Separate API + worker services with a message queue — the canonical production pattern, but adds Redis/RabbitMQ/Celery-equivalent infrastructure the master brief explicitly says not to add ("do not overengineer" — no event-streaming platforms) and that reviewers would need to additionally trust and debug.

**Consequences:** Simpler `docker compose.yml` (one service), simpler reviewer commands, and it matches the "no API key / no external infra required" constraint (NFR-06) cleanly. The production evolution path (splitting into services) is documented as a backlog item, not built.
