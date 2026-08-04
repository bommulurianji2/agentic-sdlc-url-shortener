"""Interactive demo UI - ADR-013. Not part of the core API surface
(/api/v1/...) - wraps existing functionality (the scenario scripts,
agentic.approvals) for a reviewer-facing, side-by-side showcase. No
orchestration logic is reimplemented here; every action shells out to the
same entry points a CLI user would run."""

import re
import subprocess
import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from sqlalchemy import select

from agentic import approvals
from agentic.models import WorkflowEvent, WorkflowRun
from app.database.session import SessionLocal

router = APIRouter(prefix="/demo", tags=["demo"])

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"
_PAGE_PATH = Path(__file__).resolve().parent / "demo_page.html"

SCENARIO_SCRIPTS = {
    "greenfield": "run_greenfield.py",
    "brownfield": "run_brownfield.py",
    "ambiguous": "run_ambiguous.py",
}

_WORKFLOW_ID_RE = re.compile(r"(?:Started workflow|Resuming workflow) ([0-9a-f-]{36})")


class RunRequest(BaseModel):
    scenario_type: str
    inject_failure: str | None = None
    inject_permanent_failure: bool = False


class ApproveRequest(BaseModel):
    gate: str
    decision: str
    comments: str | None = None
    inject_failure: str | None = None
    inject_permanent_failure: bool = False


def _run_script(
    script_name: str,
    *,
    workflow_id: str | None,
    inject_failure: str | None,
    inject_permanent_failure: bool,
) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, str(SCRIPTS_DIR / script_name)]
    if workflow_id:
        cmd += ["--workflow-id", workflow_id]
    if inject_failure:
        cmd += ["--inject-failure", inject_failure]
    if inject_permanent_failure:
        cmd += ["--inject-permanent-failure"]
    return subprocess.run(
        cmd, cwd=REPO_ROOT, capture_output=True, text=True, timeout=120, check=False
    )


def _workflow_status(workflow_id: str) -> dict:
    db = SessionLocal()
    try:
        run = db.get(WorkflowRun, workflow_id)
        if run is None:
            raise HTTPException(status_code=404, detail="No such workflow")
        events = db.scalars(
            select(WorkflowEvent)
            .where(WorkflowEvent.workflow_id == workflow_id)
            .order_by(WorkflowEvent.timestamp)
        ).all()
        return {
            "workflow_id": run.id,
            "scenario_type": run.scenario_type,
            "status": run.status,
            "current_stage": run.current_stage,
            "retry_count": run.retry_count,
            "rollback_count": run.rollback_count,
            "failure_count": run.failure_count,
            "events": [
                {
                    "stage": e.stage,
                    "agent": e.agent,
                    "event_type": e.event_type,
                    "decision": e.decision,
                    "reason": e.reason,
                    "timestamp": e.timestamp.isoformat(),
                    "duration_ms": e.duration_ms,
                }
                for e in events
            ],
        }
    finally:
        db.close()


@router.post("/api/workflows/run")
def run_scenario(payload: RunRequest) -> JSONResponse:
    script = SCENARIO_SCRIPTS.get(payload.scenario_type)
    if script is None:
        raise HTTPException(
            status_code=400, detail=f"Unknown scenario_type: {payload.scenario_type}"
        )

    result = _run_script(
        script,
        workflow_id=None,
        inject_failure=payload.inject_failure,
        inject_permanent_failure=payload.inject_permanent_failure,
    )
    match = _WORKFLOW_ID_RE.search(result.stdout)
    if match is None:
        detail = (
            f"Could not determine workflow id.\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )
        raise HTTPException(status_code=500, detail=detail)
    return JSONResponse(_workflow_status(match.group(1)))


@router.post("/api/workflows/{workflow_id}/approve")
def approve_and_resume(workflow_id: str, payload: ApproveRequest) -> JSONResponse:
    db = SessionLocal()
    try:
        run = db.get(WorkflowRun, workflow_id)
        if run is None:
            raise HTTPException(status_code=404, detail="No such workflow")
        script = SCENARIO_SCRIPTS[run.scenario_type]
        approvals.record_approval(
            db,
            workflow_id=workflow_id,
            gate=payload.gate,
            approver="demo-reviewer",
            decision=payload.decision,
            comments=payload.comments,
        )
    finally:
        db.close()

    _run_script(
        script,
        workflow_id=workflow_id,
        inject_failure=payload.inject_failure,
        inject_permanent_failure=payload.inject_permanent_failure,
    )
    return JSONResponse(_workflow_status(workflow_id))


@router.get("/api/workflows/{workflow_id}")
def get_workflow_status(workflow_id: str) -> JSONResponse:
    return JSONResponse(_workflow_status(workflow_id))


@router.get("", response_class=HTMLResponse)
def demo_page() -> str:
    return _PAGE_PATH.read_text(encoding="utf-8")
