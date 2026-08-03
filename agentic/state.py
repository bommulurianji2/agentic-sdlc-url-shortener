"""Coarse workflow status (this file) vs. fine graph stage (graph.py) - two
granularities by design, not two competing vocabularies. See
docs/architecture/architecture-overview.md #4.1 for the full rationale."""

from typing import Literal

WorkflowStatus = Literal[
    "CREATED",
    "ANALYSING",
    "WAITING_FOR_REQUIREMENT_APPROVAL",
    "PLANNED",
    "DESIGNING",
    "WAITING_FOR_ARCHITECTURE_APPROVAL",
    "IMPLEMENTING",
    "TESTING",
    "REVIEWING",
    "RETRYING",
    "ROLLING_BACK",
    "REPLANNING",
    "WAITING_FOR_RELEASE_APPROVAL",
    "RELEASE_READY",
    "COMPLETED",
    "REJECTED",
    "SAFE_STOPPED",
    "FAILED",
]

TERMINAL_STATUSES = {"COMPLETED", "REJECTED", "SAFE_STOPPED", "FAILED"}

# Fine graph node (agentic/graph.py) -> coarse status.
STAGE_TO_STATUS: dict[str, str] = {
    "REQUIREMENT_ANALYSIS": "ANALYSING",
    "REQUIREMENT_VALIDATION": "ANALYSING",
    "HUMAN_GATE_REQUIREMENTS": "WAITING_FOR_REQUIREMENT_APPROVAL",
    "TASK_DECOMPOSITION": "PLANNED",
    "ARCHITECTURE_DESIGN": "DESIGNING",
    "ARCHITECTURE_VALIDATION": "DESIGNING",
    "HUMAN_GATE_ARCHITECTURE": "WAITING_FOR_ARCHITECTURE_APPROVAL",
    "IMPLEMENTATION": "IMPLEMENTING",
    "TEST_DESIGN": "IMPLEMENTING",
    "JOIN": "IMPLEMENTING",
    "TEST_EXECUTION": "TESTING",
    "SECURITY_REVIEW": "REVIEWING",
    "RETRY_EVALUATION": "RETRYING",
    "ROLLBACK": "ROLLING_BACK",
    "SAFE_STOP": "SAFE_STOPPED",
    "DOCUMENTATION": "REVIEWING",
    "RELEASE_READINESS": "REVIEWING",
    "HUMAN_GATE_RELEASE": "WAITING_FOR_RELEASE_APPROVAL",
    "COMPLETE": "COMPLETED",
}


def status_for_stage(stage: str) -> str:
    return STAGE_TO_STATUS[stage]


def can_release(status: str) -> bool:
    """Single guard function, not scattered checks: only a COMPLETED run may be
    tagged/released. A SAFE_STOPPED or REJECTED run must never pass this."""
    return status == "COMPLETED"
