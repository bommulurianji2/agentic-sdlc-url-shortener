# ADR-008: CLI-based approval only; workflow approval API deferred

**Status:** Accepted

**Context:** §11 of the master brief lists "Optional workflow approval API" alongside the required CLI-based approval and persisted approval records.

**Decision:** Implement `scripts/approve_gate.py` (CLI) as the only approval mechanism. Do not add a REST endpoint for approvals.

**Alternatives considered:**
- Also expose `POST /api/v1/workflows/{id}/approvals` — would let a reviewer approve via Swagger instead of the CLI, but the master brief's own required reviewer commands (§23) are all CLI-based (`run_greenfield.py`, `approve_gate.py`, etc.); an approval API endpoint would be unused surface area, and the master brief explicitly marks it optional.

**Consequences:** One less thing to build, test, and secure (an approval endpoint would need its own auth story, which is explicitly out of scope for this prototype). Listed in the production backlog as a natural extension if this became a multi-user system.
