"""Dependency graph - docs/architecture/detailed-technical-design.md #5.
An explicit in-code structure (ADR-005), not a YAML/DSL. Includes the
SECURITY_REVIEW fail-path fix (ADR-007) that the master brief's own
diagram omitted."""

from typing import TypedDict


class NodeSpec(TypedDict, total=False):
    agent: str | None
    next: list[str] | dict[str, str]
    gate: str
    join_of: list[str]
    terminal: bool


NODES: dict[str, NodeSpec] = {
    "REQUIREMENT_ANALYSIS": {"agent": "requirement_analysis", "next": ["REQUIREMENT_VALIDATION"]},
    "REQUIREMENT_VALIDATION": {"agent": None, "next": ["HUMAN_GATE_REQUIREMENTS"]},
    "HUMAN_GATE_REQUIREMENTS": {
        "agent": None,
        "gate": "requirements",
        "next": ["TASK_DECOMPOSITION"],
    },
    "TASK_DECOMPOSITION": {"agent": "planning", "next": ["ARCHITECTURE_DESIGN"]},
    "ARCHITECTURE_DESIGN": {"agent": "architecture", "next": ["ARCHITECTURE_VALIDATION"]},
    "ARCHITECTURE_VALIDATION": {"agent": None, "next": ["HUMAN_GATE_ARCHITECTURE"]},
    "HUMAN_GATE_ARCHITECTURE": {
        "agent": None,
        "gate": "architecture",
        "next": ["IMPLEMENTATION", "TEST_DESIGN"],  # fan-out: parallel branch
    },
    "IMPLEMENTATION": {"agent": "development", "next": ["JOIN"]},
    "TEST_DESIGN": {"agent": "test", "next": ["JOIN"]},
    "JOIN": {
        "agent": None,
        "join_of": ["IMPLEMENTATION", "TEST_DESIGN"],
        "next": ["TEST_EXECUTION"],
    },
    "TEST_EXECUTION": {
        "agent": "test",
        "next": {"pass": "SECURITY_REVIEW", "fail": "RETRY_EVALUATION"},
    },
    "SECURITY_REVIEW": {
        "agent": "security_review",
        "next": {
            "pass": "DOCUMENTATION",
            "non_critical": "RETRY_EVALUATION",
            "critical": "SAFE_STOP",  # ADR-007 fix
        },
    },
    "RETRY_EVALUATION": {
        "agent": None,
        "next": {"retry": "IMPLEMENTATION", "exhausted": "ROLLBACK"},
    },
    "ROLLBACK": {"agent": None, "next": ["SAFE_STOP"]},
    "SAFE_STOP": {"agent": None, "terminal": True},
    "DOCUMENTATION": {"agent": "documentation_release", "next": ["RELEASE_READINESS"]},
    "RELEASE_READINESS": {"agent": "documentation_release", "next": ["HUMAN_GATE_RELEASE"]},
    "HUMAN_GATE_RELEASE": {"agent": None, "gate": "release", "next": ["COMPLETE"]},
    "COMPLETE": {"agent": None, "terminal": True},
}

VALID_GATES = {"requirements", "architecture", "release"}

START_NODE = "REQUIREMENT_ANALYSIS"


def is_terminal(node: str) -> bool:
    return NODES[node].get("terminal", False)


def next_nodes(node: str) -> list[str]:
    """All possible next nodes regardless of outcome - used for fan-out and for
    structural validation."""
    spec = NODES[node]
    nxt = spec.get("next")
    if nxt is None:
        return []
    if isinstance(nxt, dict):
        return list(nxt.values())
    return list(nxt)


def next_node(node: str, outcome: str | None = None) -> str:
    """Resolve the single next node for a conditional (dict-based) edge."""
    spec = NODES[node]
    nxt = spec["next"]
    if isinstance(nxt, dict):
        if outcome is None or outcome not in nxt:
            raise ValueError(f"Node '{node}' requires an outcome in {list(nxt)}, got {outcome!r}")
        return nxt[outcome]
    if len(nxt) != 1:
        raise ValueError(f"Node '{node}' has multiple next nodes; use next_nodes() for fan-out")
    return nxt[0]


def validate_graph() -> list[str]:
    """Structural self-check (ORCH-08 as executable code, not eyeballed): no
    orphan nodes, every referenced next-node exists, every gate is one of the
    three defined gates."""
    violations: list[str] = []
    for name, spec in NODES.items():
        if spec.get("terminal"):
            continue
        if "next" not in spec:
            violations.append(f"{name}: non-terminal node has no 'next'")
            continue
        for target in next_nodes(name):
            if target not in NODES:
                violations.append(f"{name}: next node '{target}' does not exist")
        gate = spec.get("gate")
        if gate is not None and gate not in VALID_GATES:
            violations.append(f"{name}: gate '{gate}' is not one of {VALID_GATES}")
    return violations
