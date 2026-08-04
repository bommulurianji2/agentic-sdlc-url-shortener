"""Shared helpers for the scenario runner scripts - not a scenario itself.
Kept as a plain sibling module (Python auto-adds a run script's own directory
to sys.path, so `from _scenario_common import ...` just works when a script
here is invoked directly, e.g. `python scripts/run_greenfield.py`)."""

import json
import sys
from pathlib import Path
from typing import cast

from sqlalchemy.orm import Session

from agentic import approvals, artifact_store, orchestrator
from agentic.context import ScenarioType, WorkflowContext
from agentic.models import WorkflowRun

GATE_BY_STATUS = {
    "WAITING_FOR_REQUIREMENT_APPROVAL": "requirements",
    "WAITING_FOR_ARCHITECTURE_APPROVAL": "architecture",
    "WAITING_FOR_RELEASE_APPROVAL": "release",
}

EVIDENCE_DIR = Path("artifacts/sample-runs")


def load_or_start(
    db: Session,
    *,
    scenario_type: ScenarioType,
    raw_requirement: str,
    workflow_id: str | None = None,
) -> tuple[WorkflowRun, WorkflowContext]:
    if workflow_id:
        run = db.get(WorkflowRun, workflow_id)
        if run is None:
            print(f"No such workflow: {workflow_id}", file=sys.stderr)
            sys.exit(1)
        context = WorkflowContext(
            workflow_id=run.id,
            # Safe cast: only start_workflow() ever writes this column, and its
            # own parameter is already typed as ScenarioType.
            scenario_type=cast(ScenarioType, run.scenario_type),
            raw_requirement=raw_requirement,
            correlation_id=run.id,
        )
        context.artifacts = artifact_store.load_context_artifacts(db, run.id)
        print(f"Resuming workflow {run.id} at stage={run.current_stage} status={run.status}")
        return run, context

    run, context = orchestrator.start_workflow(
        db, scenario_type=scenario_type, raw_requirement=raw_requirement
    )
    print(f"Started workflow {run.id}")
    return run, context


def advance(
    db: Session,
    run: WorkflowRun,
    context: WorkflowContext,
    *,
    auto_approve_demo: bool,
    approver: str = "demo-auto-approver",
) -> WorkflowRun:
    run = orchestrator.run_until_pause(db, run, context)
    print(f"status={run.status} stage={run.current_stage}")

    while auto_approve_demo and run.status in GATE_BY_STATUS:
        gate = GATE_BY_STATUS[run.status]
        approvals.record_approval(
            db,
            workflow_id=run.id,
            gate=gate,
            approver=approver,
            decision="approved",
            comments="--auto-approve-demo",
        )
        print(f"[auto-approved] gate={gate}")
        run = orchestrator.run_until_pause(db, run, context)
        print(f"status={run.status} stage={run.current_stage}")
    return run


def write_evidence(run: WorkflowRun, *, extra: dict | None = None) -> None:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    evidence = {
        "workflow_id": run.id,
        "scenario_type": run.scenario_type,
        "status": run.status,
        "current_stage": run.current_stage,
        "retry_count": run.retry_count,
        "rollback_count": run.rollback_count,
        "failure_count": run.failure_count,
        "revision": run.revision,
    }
    if extra:
        evidence.update(extra)
    path = EVIDENCE_DIR / f"{run.scenario_type}_{run.id}.json"
    path.write_text(json.dumps(evidence, indent=2, default=str), encoding="utf-8")
    print(f"Evidence written to {path}")


def next_action_hint(run: WorkflowRun, script_name: str) -> str:
    if run.status in GATE_BY_STATUS:
        gate = GATE_BY_STATUS[run.status]
        return (
            f"Next: approve or reject this gate, then resume:\n"
            f"  python scripts/approve_gate.py {run.id} {gate} approved\n"
            f"  python scripts/{script_name} --workflow-id {run.id}"
        )
    if run.status == "COMPLETED":
        return "Workflow COMPLETED - release-ready evidence written."
    if run.status == "SAFE_STOPPED":
        return "Workflow SAFE_STOPPED - release is blocked; see workflow_events for why."
    if run.status == "REJECTED":
        return "Workflow REJECTED at a gate - no further action; a new run is needed."
    return f"Workflow stopped at status={run.status}."
