"""Prototype reliability metrics - METRIC-01.
docs/architecture/detailed-technical-design.md #9. Explicitly prototype-scale
metrics, not production SLIs - labelled as such in every report."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from agentic.models import Artifact, WorkflowEvent, WorkflowRun
from agentic.state import TERMINAL_STATUSES


def success_rate(db: Session) -> float:
    runs = list(db.scalars(select(WorkflowRun)))
    terminal = [r for r in runs if r.status in TERMINAL_STATUSES]
    if not terminal:
        return 0.0
    completed = [r for r in terminal if r.status == "COMPLETED"]
    return len(completed) / len(terminal)


def retry_frequency(db: Session) -> float:
    runs = list(db.scalars(select(WorkflowRun)))
    return sum(r.retry_count for r in runs) / len(runs) if runs else 0.0


def rollback_frequency(db: Session) -> float:
    runs = list(db.scalars(select(WorkflowRun)))
    return sum(r.rollback_count for r in runs) / len(runs) if runs else 0.0


def failed_stage_frequency(db: Session) -> dict[str, int]:
    events = db.scalars(select(WorkflowEvent).where(WorkflowEvent.event_type == "stage_failure"))
    counts: dict[str, int] = {}
    for event in events:
        counts[event.stage] = counts.get(event.stage, 0) + 1
    return counts


def replanning_count(db: Session) -> int:
    return len(list(db.scalars(select(WorkflowEvent).where(WorkflowEvent.event_type == "replan"))))


def end_to_end_latency_seconds(run: WorkflowRun) -> float | None:
    if run.completed_at is None:
        return None
    return (run.completed_at - run.started_at).total_seconds()


def agent_step_latency_ms(db: Session) -> dict[str, float]:
    events = db.scalars(select(WorkflowEvent).where(WorkflowEvent.duration_ms.is_not(None)))
    by_agent: dict[str, list[int]] = {}
    for event in events:
        if event.agent and event.duration_ms is not None:
            by_agent.setdefault(event.agent, []).append(event.duration_ms)
    return {agent: sum(durations) / len(durations) for agent, durations in by_agent.items()}


def artifact_first_pass_acceptance_rate(db: Session) -> float:
    v1_artifacts = list(db.scalars(select(Artifact).where(Artifact.version == 1)))
    if not v1_artifacts:
        return 0.0
    approved_v1 = [a for a in v1_artifacts if a.status == "approved"]
    return len(approved_v1) / len(v1_artifacts)


def generate_report(db: Session) -> dict:
    """scripts/generate_metrics.py prints this. Not every metric in the master
    brief's list is implemented (approval-waiting-time and MTTR need more
    workflow_events history than a small prototype run naturally accumulates) -
    this report only claims what it actually computes."""
    return {
        "disclaimer": "Prototype-scale metrics, not production SLIs.",
        "success_rate": success_rate(db),
        "retry_frequency": retry_frequency(db),
        "rollback_frequency": rollback_frequency(db),
        "failed_stage_frequency": failed_stage_frequency(db),
        "replanning_count": replanning_count(db),
        "agent_step_latency_ms": agent_step_latency_ms(db),
        "artifact_first_pass_acceptance_rate": artifact_first_pass_acceptance_rate(db),
    }
