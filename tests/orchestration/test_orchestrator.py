from unittest.mock import MagicMock, patch

from agentic import approvals, orchestrator


def _approve(db, run, gate):
    approvals.record_approval(
        db, workflow_id=run.id, gate=gate, approver="test-reviewer", decision="approved"
    )


def _subprocess_stub(passed: int = 10, failed: int = 0):
    """A single side_effect for the one real, global `subprocess.run` - patching
    it via two different modules' import paths (agentic.agents.test_agent.subprocess.run
    AND agentic.agents.security_review_agent.subprocess.run) is a mocking trap:
    both names refer to the exact same global `subprocess` module object, so the
    second @patch silently clobbers the first for the whole test. One patch on
    the canonical "subprocess.run", dispatching on the command, avoids that."""

    def _run(cmd, **kwargs):
        result = MagicMock()
        if cmd and cmd[0] == "pytest":
            result.stdout = (
                f"{passed} passed" + (f", {failed} failed" if failed else "") + " in 0.1s"
            )
        else:
            result.returncode = 0
            result.stdout = ""
        return result

    return _run


@patch("subprocess.run")
def test_full_greenfield_workflow_completes_with_all_gates_approved(mock_run, db_session):
    mock_run.side_effect = _subprocess_stub(passed=10, failed=0)

    run, context = orchestrator.start_workflow(
        db_session, scenario_type="greenfield", raw_requirement="Build a URL shortener."
    )

    run = orchestrator.run_until_pause(db_session, run, context)
    assert run.status == "WAITING_FOR_REQUIREMENT_APPROVAL"
    _approve(db_session, run, "requirements")

    run = orchestrator.run_until_pause(db_session, run, context)
    assert run.status == "WAITING_FOR_ARCHITECTURE_APPROVAL"
    _approve(db_session, run, "architecture")

    run = orchestrator.run_until_pause(db_session, run, context)
    assert run.status == "WAITING_FOR_RELEASE_APPROVAL"
    _approve(db_session, run, "release")

    run = orchestrator.run_until_pause(db_session, run, context)
    assert run.status == "COMPLETED"
    assert run.completed_at is not None
    assert run.retry_count == 0
    assert run.rollback_count == 0


def test_requirement_gate_rejection_stops_the_workflow(db_session):
    run, context = orchestrator.start_workflow(
        db_session, scenario_type="greenfield", raw_requirement="Build a URL shortener."
    )
    run = orchestrator.run_until_pause(db_session, run, context)
    assert run.status == "WAITING_FOR_REQUIREMENT_APPROVAL"

    approvals.record_approval(
        db_session,
        workflow_id=run.id,
        gate="requirements",
        approver="test-reviewer",
        decision="rejected",
        comments="scope needs rework",
    )
    run = orchestrator.run_until_pause(db_session, run, context)
    assert run.status == "REJECTED"


@patch("subprocess.run")
def test_retry_exhaustion_leads_to_rollback_and_safe_stop(mock_run, db_session):
    mock_run.side_effect = _subprocess_stub(passed=0, failed=1)

    run, context = orchestrator.start_workflow(
        db_session, scenario_type="greenfield", raw_requirement="Build a URL shortener."
    )
    context.flags["inject_failure"] = "test_execution"  # fails every retry attempt

    run = orchestrator.run_until_pause(db_session, run, context)
    _approve(db_session, run, "requirements")
    run = orchestrator.run_until_pause(db_session, run, context)
    _approve(db_session, run, "architecture")

    run = orchestrator.run_until_pause(db_session, run, context)

    assert run.status == "SAFE_STOPPED"
    assert run.retry_count == 2  # MAX_RETRIES
    assert run.rollback_count == 1

    from agentic.state import can_release

    assert can_release(run.status) is False


@patch("subprocess.run")
def test_critical_security_finding_safe_stops_without_using_a_retry(mock_run, db_session):
    mock_run.side_effect = _subprocess_stub(passed=10, failed=0)

    run, context = orchestrator.start_workflow(
        db_session, scenario_type="greenfield", raw_requirement="Build a URL shortener."
    )
    context.flags["inject_permanent_failure"] = True  # critical finding at SECURITY_REVIEW

    run = orchestrator.run_until_pause(db_session, run, context)
    _approve(db_session, run, "requirements")
    run = orchestrator.run_until_pause(db_session, run, context)
    _approve(db_session, run, "architecture")

    run = orchestrator.run_until_pause(db_session, run, context)

    assert run.status == "SAFE_STOPPED"
    assert run.retry_count == 0  # ADR-007: critical routes straight to SAFE_STOP, no retry spent
