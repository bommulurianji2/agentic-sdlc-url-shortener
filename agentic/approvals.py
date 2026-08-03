"""Human approval gates - GOV-01. docs/architecture/detailed-technical-design.md #1."""

import json
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from agentic.artifact_store import approve_artifact
from agentic.models import Approval, Artifact
from app.time_utils import utc_now

VALID_GATES = {"requirements", "architecture", "release"}
VALID_DECISIONS = {"approved", "rejected"}

# Which artifact_types a gate approval covers - Gate 2 bundles the plan +
# architecture together (per this project's own Gate 2 staging decision);
# Gate 3 bundles everything that feeds the release-readiness recommendation.
GATE_ARTIFACT_TYPES = {
    "requirements": ["requirement"],
    "architecture": ["plan", "architecture"],
    "release": ["development", "test", "security_review", "release"],
}


def record_approval(
    db: Session,
    *,
    workflow_id: str,
    gate: str,
    approver: str,
    decision: str,
    comments: str | None = None,
    artifact_versions: dict[str, int] | None = None,
) -> Approval:
    if gate not in VALID_GATES:
        raise ValueError(f"gate must be one of {VALID_GATES}, got {gate!r}")
    if decision not in VALID_DECISIONS:
        raise ValueError(f"decision must be one of {VALID_DECISIONS}, got {decision!r}")

    approval = Approval(
        id=str(uuid.uuid4()),
        workflow_id=workflow_id,
        gate=gate,
        approver=approver,
        decision=decision,
        comments=comments,
        artifact_versions=json.dumps(artifact_versions or {}),
        timestamp=utc_now(),
    )
    db.add(approval)
    db.commit()

    if decision == "approved":
        for artifact_type in GATE_ARTIFACT_TYPES[gate]:
            latest = db.scalar(
                select(Artifact)
                .where(Artifact.workflow_id == workflow_id, Artifact.artifact_type == artifact_type)
                .order_by(Artifact.version.desc())
            )
            if latest is not None:
                approve_artifact(db, latest)

    return approval


def latest_decision(db: Session, workflow_id: str, gate: str) -> Approval | None:
    return db.scalar(
        select(Approval)
        .where(Approval.workflow_id == workflow_id, Approval.gate == gate)
        .order_by(Approval.timestamp.desc())
    )


def is_approved(db: Session, workflow_id: str, gate: str) -> bool:
    decision = latest_decision(db, workflow_id, gate)
    return decision is not None and decision.decision == "approved"


def is_rejected(db: Session, workflow_id: str, gate: str) -> bool:
    decision = latest_decision(db, workflow_id, gate)
    return decision is not None and decision.decision == "rejected"
