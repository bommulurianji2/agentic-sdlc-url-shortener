"""Tests for the demo router (ADR-013). subprocess.run is mocked throughout -
these test the router's own wiring (parsing, DB reads, approval recording),
not the scenario scripts themselves, which already have their own coverage
in tests/orchestration/."""

from unittest.mock import MagicMock, patch

from agentic import approvals
from agentic.models import WorkflowRun
from app.time_utils import utc_now


def _make_run(
    db_session, workflow_id: str, status: str = "WAITING_FOR_REQUIREMENT_APPROVAL"
) -> None:
    db_session.add(
        WorkflowRun(
            id=workflow_id,
            scenario_type="greenfield",
            status=status,
            current_stage="HUMAN_GATE_REQUIREMENTS",
            started_at=utc_now(),
        )
    )
    db_session.commit()


def test_demo_page_loads(client):
    response = client.get("/demo")
    assert response.status_code == 200
    assert "Agentic SDLC URL Shortener" in response.text
    assert "Agentic Governance" in response.text


def test_run_scenario_rejects_unknown_scenario_type(client):
    response = client.post("/demo/api/workflows/run", json={"scenario_type": "not-a-scenario"})
    assert response.status_code == 400


@patch("app.api.demo.subprocess.run")
def test_run_scenario_parses_workflow_id_and_returns_status(mock_run, client, db_session):
    workflow_id = "11111111-1111-1111-1111-111111111111"
    _make_run(db_session, workflow_id)
    mock_run.return_value = MagicMock(
        stdout=f"Started workflow {workflow_id}\nstatus=WAITING_FOR_REQUIREMENT_APPROVAL\n",
        returncode=0,
    )

    response = client.post("/demo/api/workflows/run", json={"scenario_type": "greenfield"})
    assert response.status_code == 200
    body = response.json()
    assert body["workflow_id"] == workflow_id
    assert body["status"] == "WAITING_FOR_REQUIREMENT_APPROVAL"
    assert body["events"] == []  # no events written by the (mocked) script in this test


@patch("app.api.demo.subprocess.run")
def test_run_scenario_500s_if_workflow_id_cannot_be_parsed(mock_run, client):
    mock_run.return_value = MagicMock(stdout="no id printed here", returncode=0)
    response = client.post("/demo/api/workflows/run", json={"scenario_type": "greenfield"})
    assert response.status_code == 500


def test_get_workflow_status_404_for_unknown_id(client):
    response = client.get("/demo/api/workflows/does-not-exist")
    assert response.status_code == 404


@patch("app.api.demo.subprocess.run")
def test_approve_and_resume_records_approval_and_invokes_resume(mock_run, client, db_session):
    workflow_id = "22222222-2222-2222-2222-222222222222"
    _make_run(db_session, workflow_id)
    mock_run.return_value = MagicMock(stdout="", returncode=0)

    response = client.post(
        f"/demo/api/workflows/{workflow_id}/approve",
        json={"gate": "requirements", "decision": "approved"},
    )
    assert response.status_code == 200
    assert approvals.is_approved(db_session, workflow_id, "requirements") is True

    called_cmd = mock_run.call_args.args[0]
    assert "--workflow-id" in called_cmd
    assert workflow_id in called_cmd
    assert "run_greenfield.py" in called_cmd[1]


@patch("app.api.demo.subprocess.run")
def test_approve_passes_injection_flags_through(mock_run, client, db_session):
    workflow_id = "33333333-3333-3333-3333-333333333333"
    _make_run(db_session, workflow_id)
    mock_run.return_value = MagicMock(stdout="", returncode=0)

    client.post(
        f"/demo/api/workflows/{workflow_id}/approve",
        json={
            "gate": "requirements",
            "decision": "approved",
            "inject_failure": "test_execution",
            "inject_permanent_failure": True,
        },
    )
    called_cmd = mock_run.call_args.args[0]
    assert "--inject-failure" in called_cmd
    assert "test_execution" in called_cmd
    assert "--inject-permanent-failure" in called_cmd


def test_approve_404s_for_unknown_workflow(client):
    response = client.post(
        "/demo/api/workflows/does-not-exist/approve",
        json={"gate": "requirements", "decision": "approved"},
    )
    assert response.status_code == 404
