"""Rollback - GOV-04. docs/architecture/detailed-technical-design.md #12."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from agentic.models import Artifact, WorkflowRun


def rollback(db: Session, run: WorkflowRun) -> None:
    """Supersedes any draft/stale artifact versions (the last *approved* version,
    if any, is left untouched - restored, not deleted), increments rollback_count,
    and always ends in SAFE_STOPPED. Re-entry requires a human decision (re-approve
    or replan) - never an automatic resume (GOV-04/GOV-05)."""
    drafts_and_stale = db.scalars(
        select(Artifact).where(
            Artifact.workflow_id == run.id,
            Artifact.status.in_(["draft", "stale"]),
        )
    )
    for artifact in drafts_and_stale:
        artifact.status = "superseded"

    run.rollback_count += 1
    run.status = "SAFE_STOPPED"
    run.current_stage = "SAFE_STOP"
    db.commit()
