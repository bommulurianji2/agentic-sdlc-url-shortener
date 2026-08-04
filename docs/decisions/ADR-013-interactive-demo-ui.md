# ADR-013: Interactive demo UI adds a browser-facing approval surface, alongside (not instead of) CLI-only approval

**Status:** Accepted

**Context:** ADR-008 established CLI-only approval for the core system, specifically to avoid needing a multi-user auth story for a prototype. A reviewer-facing demo UI (`/demo`) now needs a "Run" and "Approve" button in the browser to visually showcase the real orchestration graph, gates, and agents side by side with the application's own functionality.

**Decision:** Add two new, demo-scoped endpoints (`app/api/demo.py`) that wrap the *same* underlying functions the CLI already uses — `agentic.approvals.record_approval()` for approval, and the same `scripts/run_<scenario>.py` entry points (invoked as a subprocess) for running/resuming a workflow. No orchestration logic is reimplemented. A browser click is still a real human decision recorded in the `approvals` table exactly like a CLI invocation — GOV-01 is unaffected. What changes is the *interface*, not the *governance*.

**Alternatives considered:**
- Read-only demo (visualize CLI-triggered runs, no browser-side actions) — simpler and adds zero new write surface, but far less compelling to watch live, and the reviewer explicitly asked for the more interactive version having weighed the trade-off.
- Reimplementing approval/orchestration logic directly in the web layer — rejected; would create two divergent code paths for the same governance decision, exactly the kind of duplication the rest of this system avoids.

**Consequences:** The running container now has a new capability (triggering scenario runs and recording approvals from a browser) that didn't exist before. This is acceptable for a demo/reviewer-facing prototype and is explicitly scoped as such — `/demo` is not part of the application's core API surface (`/api/v1/...`) and is not implied to be production-appropriate as-is (no auth on these endpoints; fine for a local/reviewer demo, not for a multi-user deployment).
