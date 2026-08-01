# ADR-005: Workflow graph as an explicit in-code data structure

**Status:** Accepted

**Context:** ORCH-08 requires the dependency graph to exist in "executable configuration or code — not only as documentation."

**Decision:** `agentic/graph.py` defines nodes and edges as a plain Python data structure (dict of node → {agent, entry_criteria, exit_criteria, edges: [(condition, next_node)]}), which `orchestrator.py` walks at runtime. No graph DSL, no YAML workflow engine.

**Alternatives considered:**
- YAML/JSON workflow definition parsed at runtime — adds a parsing/validation layer for no real benefit at this scale, and a plain Python dict is just as inspectable and is trivially unit-testable (assert edges exist, assert no orphan nodes) without a schema validator.

**Consequences:** The graph is versioned with the rest of the code (a graph change shows up in a normal code diff/PR), and `tests/orchestration` can assert directly on `graph.NODES`/`graph.EDGES` rather than parsing a config file.
