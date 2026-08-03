"""Artifact versioning and storage - docs/architecture/detailed-technical-design.md #10.
GOV-07 as code: a rejected draft never displaces an approved version."""

import hashlib
import json
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from agentic.models import Artifact
from app.time_utils import utc_now

ARTIFACT_ROOT = Path("artifacts/runtime")


def _checksum(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _serialize(content: Any) -> str:
    if hasattr(content, "model_dump_json"):
        return content.model_dump_json(indent=2)
    return json.dumps(content, indent=2, default=str)


def save_artifact(
    db: Session,
    *,
    workflow_id: str,
    artifact_type: str,
    content: Any,
    created_by: str,
) -> Artifact:
    """version=1 if none exists yet for this (workflow_id, artifact_type); else
    previous+1, and only if the content actually changed - identical content
    returns the existing version rather than writing a no-op duplicate."""
    serialized = _serialize(content)
    checksum = _checksum(serialized)

    latest = db.scalar(
        select(Artifact)
        .where(Artifact.workflow_id == workflow_id, Artifact.artifact_type == artifact_type)
        .order_by(Artifact.version.desc())
    )
    if latest is not None and latest.checksum == checksum:
        return latest

    version = 1 if latest is None else latest.version + 1
    ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
    content_path = ARTIFACT_ROOT / f"{workflow_id}_{artifact_type}_v{version}.json"
    content_path.write_text(serialized, encoding="utf-8")

    artifact = Artifact(
        id=str(uuid.uuid4()),
        workflow_id=workflow_id,
        artifact_type=artifact_type,
        version=version,
        status="draft",
        content_path=str(content_path),
        checksum=checksum,
        created_by=created_by,
        created_at=utc_now(),
    )
    db.add(artifact)
    db.commit()
    return artifact


def approve_artifact(db: Session, artifact: Artifact) -> None:
    """A newly-approved version supersedes the previous approved one - never
    the other way around, so a later-rejected draft can't displace it."""
    previous_approved = db.scalar(
        select(Artifact).where(
            Artifact.workflow_id == artifact.workflow_id,
            Artifact.artifact_type == artifact.artifact_type,
            Artifact.status == "approved",
        )
    )
    if previous_approved is not None and previous_approved.id != artifact.id:
        previous_approved.status = "superseded"
    artifact.status = "approved"
    db.commit()


def mark_stale(db: Session, workflow_id: str, artifact_type: str) -> None:
    artifact = db.scalar(
        select(Artifact)
        .where(Artifact.workflow_id == workflow_id, Artifact.artifact_type == artifact_type)
        .order_by(Artifact.version.desc())
    )
    if artifact is not None:
        artifact.status = "stale"
        db.commit()


def verify_checksum(artifact: Artifact) -> bool:
    content = Path(artifact.content_path).read_text(encoding="utf-8")
    return _checksum(content) == artifact.checksum
