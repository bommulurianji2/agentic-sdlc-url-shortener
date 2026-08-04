import uuid

from agentic import metrics
from agentic.models import Artifact, WorkflowEvent, WorkflowRun
from app.time_utils import utc_now


def _run(**overrides) -> WorkflowRun:
    defaults = dict(
        id=str(uuid.uuid4()),
        scenario_type="greenfield",
        status="COMPLETED",
        current_stage="COMPLETE",
        started_at=utc_now(),
        retry_count=0,
        rollback_count=0,
        failure_count=0,
    )
    defaults.update(overrides)
    return WorkflowRun(**defaults)


def test_success_rate_counts_only_terminal_runs(db_session):
    db_session.add_all(
        [
            _run(status="COMPLETED"),
            _run(status="COMPLETED"),
            _run(status="SAFE_STOPPED"),
            _run(status="TESTING"),  # not terminal - excluded
        ]
    )
    db_session.commit()
    assert metrics.success_rate(db_session) == 2 / 3


def test_success_rate_with_no_runs_is_zero(db_session):
    assert metrics.success_rate(db_session) == 0.0


def test_retry_and_rollback_frequency_average_across_runs(db_session):
    db_session.add_all(
        [_run(retry_count=2, rollback_count=1), _run(retry_count=0, rollback_count=0)]
    )
    db_session.commit()
    assert metrics.retry_frequency(db_session) == 1.0
    assert metrics.rollback_frequency(db_session) == 0.5


def test_failed_stage_frequency_counts_per_stage(db_session):
    run = _run()
    db_session.add(run)
    db_session.commit()
    for stage in ("TEST_EXECUTION", "TEST_EXECUTION", "SECURITY_REVIEW"):
        db_session.add(
            WorkflowEvent(
                id=str(uuid.uuid4()),
                workflow_id=run.id,
                agent=None,
                stage=stage,
                event_type="stage_failure",
                timestamp=utc_now(),
                correlation_id=run.id,
            )
        )
    db_session.commit()
    assert metrics.failed_stage_frequency(db_session) == {"TEST_EXECUTION": 2, "SECURITY_REVIEW": 1}


def test_replanning_count(db_session):
    run = _run()
    db_session.add(run)
    db_session.add(
        WorkflowEvent(
            id=str(uuid.uuid4()),
            workflow_id=run.id,
            agent=None,
            stage="TASK_DECOMPOSITION",
            event_type="replan",
            timestamp=utc_now(),
            correlation_id=run.id,
        )
    )
    db_session.commit()
    assert metrics.replanning_count(db_session) == 1


def test_end_to_end_latency_is_none_when_not_completed(db_session):
    run = _run(completed_at=None)
    assert metrics.end_to_end_latency_seconds(run) is None


def test_end_to_end_latency_computes_duration():
    import datetime as dt

    started = utc_now()
    run = _run(started_at=started, completed_at=started + dt.timedelta(seconds=5))
    assert metrics.end_to_end_latency_seconds(run) == 5.0


def test_agent_step_latency_averages_per_agent(db_session):
    run = _run()
    db_session.add(run)
    for duration in (100, 200):
        db_session.add(
            WorkflowEvent(
                id=str(uuid.uuid4()),
                workflow_id=run.id,
                agent="development",
                stage="IMPLEMENTATION",
                event_type="stage_success",
                timestamp=utc_now(),
                duration_ms=duration,
                correlation_id=run.id,
            )
        )
    db_session.commit()
    assert metrics.agent_step_latency_ms(db_session) == {"development": 150.0}


def test_artifact_first_pass_acceptance_rate(db_session):
    run = _run()
    db_session.add(run)
    db_session.add_all(
        [
            Artifact(
                id=str(uuid.uuid4()),
                workflow_id=run.id,
                artifact_type="requirement",
                version=1,
                status="approved",
                content_path="x",
                checksum="x",
                created_by="requirement_analysis",
                created_at=utc_now(),
            ),
            Artifact(
                id=str(uuid.uuid4()),
                workflow_id=run.id,
                artifact_type="architecture",
                version=1,
                status="stale",
                content_path="x",
                checksum="y",
                created_by="architecture",
                created_at=utc_now(),
            ),
        ]
    )
    db_session.commit()
    assert metrics.artifact_first_pass_acceptance_rate(db_session) == 0.5


def test_generate_report_includes_the_prototype_disclaimer(db_session):
    report = metrics.generate_report(db_session)
    assert "prototype" in report["disclaimer"].lower()
    assert "success_rate" in report
