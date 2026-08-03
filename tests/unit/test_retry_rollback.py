from agentic import retry, rollback
from agentic.artifact_store import save_artifact
from agentic.models import WorkflowRun
from app.time_utils import utc_now


def test_retry_is_bounded_at_two(db_session):
    run = WorkflowRun(
        id="wf-r1",
        scenario_type="greenfield",
        status="TESTING",
        current_stage="TEST_EXECUTION",
        started_at=utc_now(),
    )
    db_session.add(run)
    db_session.commit()  # SQLAlchemy column defaults (retry_count=0) apply at INSERT

    assert retry.evaluate_retry(run, retryable=True) == "retry"
    assert run.retry_count == 1
    assert retry.evaluate_retry(run, retryable=True) == "retry"
    assert run.retry_count == 2
    assert retry.evaluate_retry(run, retryable=True) == "exhausted"
    assert run.retry_count == 2  # not incremented past the bound


def test_non_retryable_failure_is_immediately_exhausted(db_session):
    run = WorkflowRun(
        id="wf-r2",
        scenario_type="greenfield",
        status="TESTING",
        current_stage="TEST_EXECUTION",
        started_at=utc_now(),
    )
    db_session.add(run)
    db_session.commit()

    assert retry.evaluate_retry(run, retryable=False) == "exhausted"
    assert run.retry_count == 0


def test_rollback_supersedes_drafts_and_stale_but_not_approved(db_session):
    run = WorkflowRun(
        id="wf-r3",
        scenario_type="greenfield",
        status="TESTING",
        current_stage="TEST_EXECUTION",
        started_at=utc_now(),
    )
    db_session.add(run)
    db_session.commit()

    approved = save_artifact(
        db_session,
        workflow_id=run.id,
        artifact_type="requirement",
        content={"a": 1},
        created_by="requirement_analysis",
    )
    from agentic.artifact_store import approve_artifact

    approve_artifact(db_session, approved)

    draft = save_artifact(
        db_session,
        workflow_id=run.id,
        artifact_type="development",
        content={"b": 1},
        created_by="development",
    )

    rollback.rollback(db_session, run)

    db_session.refresh(approved)
    db_session.refresh(draft)
    assert approved.status == "approved"  # untouched - it was already approved
    assert draft.status == "superseded"
    assert run.status == "SAFE_STOPPED"
    assert run.current_stage == "SAFE_STOP"
    assert run.rollback_count == 1
