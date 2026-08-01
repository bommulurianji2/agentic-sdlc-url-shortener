# ADR-011: Agent tool-allowlisting is satisfied by construction in deterministic mode

**Status:** Accepted

**Context:** §6 of the master brief requires "Agent tools must be allowlisted" and that agents cannot deploy to production, bypass gates, or take destructive action. These read as controls for an autonomous, tool-calling LLM agent architecture.

**Decision:** In deterministic mode, agents (`agentic/agents/*.py`) are plain functions: they read a `WorkflowContext`, compute a result, and return an `AgentResult`. They have no shell access, no network access, no arbitrary filesystem access (writes are only ever through `agentic/artifact_store.py`), and no ability to invoke `docker`/`git push`/deployment commands. The controls in §6 are therefore true by construction — there is no capability to restrict, because the capability doesn't exist — rather than enforced by a runtime policy check.

**Alternatives considered:**
- Build a real tool-calling loop with an explicit allowlist check even in deterministic mode, so the enforcement mechanism is identical in both modes — rejected as pure overhead for this prototype: deterministic agents never call tools at all, so a permission check that only ever sees zero tool-call attempts adds code with nothing to verify.

**Consequences:** If the optional live-LLM mode (`agentic/llm_provider.py`) is ever built out, it introduces a genuine tool-calling surface (an LLM could attempt to request an action) and **would need its own real allowlist enforcement at that point** — this ADR exists specifically so that future work doesn't assume §6 is "already handled" for the LLM path just because it's handled for the deterministic one. Tracked as a production/future-mode backlog item.
