from agentic import artifact_store
from agentic.models import WorkflowRun
from app.time_utils import utc_now


def _make_run(db_session, workflow_id: str = "wf-1") -> None:
    db_session.add(
        WorkflowRun(
            id=workflow_id,
            scenario_type="greenfield",
            status="ANALYSING",
            current_stage="REQUIREMENT_ANALYSIS",
            started_at=utc_now(),
        )
    )
    db_session.commit()


def test_save_artifact_creates_version_one(db_session):
    _make_run(db_session)
    artifact = artifact_store.save_artifact(
        db_session,
        workflow_id="wf-1",
        artifact_type="requirement",
        content={"normalized_requirement": "x"},
        created_by="requirement_analysis",
    )
    assert artifact.version == 1
    assert artifact.status == "draft"


def test_save_artifact_bumps_version_on_material_change(db_session):
    _make_run(db_session)
    artifact_store.save_artifact(
        db_session,
        workflow_id="wf-1",
        artifact_type="requirement",
        content={"a": 1},
        created_by="requirement_analysis",
    )
    v2 = artifact_store.save_artifact(
        db_session,
        workflow_id="wf-1",
        artifact_type="requirement",
        content={"a": 2},
        created_by="requirement_analysis",
    )
    assert v2.version == 2


def test_save_artifact_is_a_noop_when_content_is_unchanged(db_session):
    _make_run(db_session)
    v1 = artifact_store.save_artifact(
        db_session,
        workflow_id="wf-1",
        artifact_type="requirement",
        content={"a": 1},
        created_by="requirement_analysis",
    )
    v1_again = artifact_store.save_artifact(
        db_session,
        workflow_id="wf-1",
        artifact_type="requirement",
        content={"a": 1},
        created_by="requirement_analysis",
    )
    assert v1.id == v1_again.id
    assert v1_again.version == 1


def test_approving_a_new_version_supersedes_the_old_approved_one(db_session):
    _make_run(db_session)
    v1 = artifact_store.save_artifact(
        db_session,
        workflow_id="wf-1",
        artifact_type="architecture",
        content={"a": 1},
        created_by="architecture",
    )
    artifact_store.approve_artifact(db_session, v1)
    assert v1.status == "approved"

    v2 = artifact_store.save_artifact(
        db_session,
        workflow_id="wf-1",
        artifact_type="architecture",
        content={"a": 2},
        created_by="architecture",
    )
    artifact_store.approve_artifact(db_session, v2)

    db_session.refresh(v1)
    assert v1.status == "superseded"
    assert v2.status == "approved"


def test_checksum_verification_detects_tampering(db_session, tmp_path):
    _make_run(db_session)
    artifact = artifact_store.save_artifact(
        db_session,
        workflow_id="wf-1",
        artifact_type="requirement",
        content={"a": 1},
        created_by="requirement_analysis",
    )
    assert artifact_store.verify_checksum(artifact) is True

    from pathlib import Path

    Path(artifact.content_path).write_text("tampered", encoding="utf-8")
    assert artifact_store.verify_checksum(artifact) is False
