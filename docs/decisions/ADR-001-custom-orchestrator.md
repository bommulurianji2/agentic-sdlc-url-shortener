# ADR-001: Custom dependency-graph orchestrator instead of a third-party agent framework

**Status:** Accepted

**Context:** The system needs stateful, non-linear, dependency-graph-driven execution with parallel branches, retries, rollback, and human gates (ORCH-06…09, GOV-01…05). Frameworks like LangGraph or CrewAI could provide some of this off the shelf.

**Decision:** Build a small, custom Python state machine + dependency graph (`agentic/graph.py`, `orchestrator.py`, `state.py`) rather than adopting a third-party agent framework, per binding assumption §3.11.

**Alternatives considered:**
- A LangGraph-style framework — would satisfy the graph/state requirements but adds a dependency the reviewer must trust and understand, and its retry/rollback/safe-stop semantics don't map 1:1 onto this system's specific governance model (GOV-01…07), so we'd end up fighting the framework's opinions as much as using them.
- A pure linear script with if/else — fails ORCH-07 (non-linear) and ORCH-09 (parallel+join) outright.

**Consequences:** More code to write and test ourselves, but every line is inspectable by a reviewer with no framework-specific knowledge required, and the graph/state model can be shaped exactly to this system's gates and retry policy.
