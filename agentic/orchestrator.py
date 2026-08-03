"""SDLC Orchestrator - docs/architecture/detailed-technical-design.md #4/#5.

Walks the dependency graph (agentic/graph.py), invoking the responsible agent
at each node, persisting state/events/artifacts, and applying governance
policies (retry/rollback/safe-stop/gates). The orchestrator itself never
produces an engineering artifact, only routes and enforces (master brief #7.1).

Design note on the two nodes that don't fit the generic node-by-node walk:
IMPLEMENTATION triggers the one modeled parallel branch (ORCH-09, ADR-010) -
running TEST_DESIGN concurrently and collapsing JOIN into the same step,
whichever path reached IMPLEMENTATION (initial fan-out from
HUMAN_GATE_ARCHITECTURE, or a retry loop-back). TEST_EXECUTION and
SECURITY_REVIEW resolve conditional (dict-keyed) edges from their own
AgentResult. Every other node advances along the graph's plain list edge.

Nodes with no modeled retry path (everything except TEST_EXECUTION and
SECURITY_REVIEW, matching the master brief's own graph) go to FAILED, not
SAFE_STOPPED, if their agent unexpectedly fails - FAILED is an uncontrolled
error, SAFE_STOPPED is a controlled policy decision (see agentic/state.py)."""

import json
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy.orm import Session

from agentic import approvals, graph, retry, rollback, state
from agentic.agents import REGISTRY
from agentic.agents.base import AgentResult
from agentic.artifact_store import save_artifact
from agentic.context import ScenarioType, WorkflowContext
from agentic.models import WorkflowEvent, WorkflowRun
from app.time_utils import utc_now

_SIMPLE_AGENT_NODES = {
    "REQUIREMENT_ANALYSIS",
    "REQUIREMENT_VALIDATION",
    "TASK_DECOMPOSITION",
    "ARCHITECTURE_DESIGN",
    "ARCHITECTURE_VALIDATION",
    "DOCUMENTATION",
    "RELEASE_READINESS",
}


def start_workflow(
    db: Session,
    *,
    scenario_type: ScenarioType,
    raw_requirement: str,
    correlation_id: str | None = None,
) -> tuple[WorkflowRun, WorkflowContext]:
    workflow_id = str(uuid.uuid4())
    run = WorkflowRun(
        id=workflow_id,
        scenario_type=scenario_type,
        status=state.STAGE_TO_STATUS[graph.START_NODE],
        current_stage=graph.START_NODE,
        started_at=utc_now(),
    )
    db.add(run)
    db.commit()

    context = WorkflowContext(
        workflow_id=workflow_id,
        scenario_type=scenario_type,
        raw_requirement=raw_requirement,
        correlation_id=correlation_id or str(uuid.uuid4()),
    )
    return run, context


def _log_event(
    db: Session,
    run: WorkflowRun,
    *,
    agent: str | None,
    stage: str,
    event_type: str,
    reason: str | None = None,
    decision: str | None = None,
    duration_ms: int | None = None,
    output_artifacts: list[str] | None = None,
) -> None:
    db.add(
        WorkflowEvent(
            id=str(uuid.uuid4()),
            workflow_id=run.id,
            agent=agent,
            stage=stage,
            event_type=event_type,
            input_artifact_ids=json.dumps([]),
            output_artifact_ids=json.dumps(output_artifacts or []),
            decision=decision,
            reason=reason,
            timestamp=utc_now(),
            duration_ms=duration_ms,
            error_details=None if event_type != "stage_failure" else reason,
            correlation_id=run.id,
        )
    )
    db.commit()


def _execute_agent(context: WorkflowContext, node: str, agent_name: str) -> tuple[AgentResult, int]:
    """Pure computation, no DB access - safe to run concurrently in a thread
    (SQLAlchemy Sessions are not thread-safe, so DB writes always happen
    afterward on the caller's thread; see _persist_agent_result)."""
    context.flags["stage"] = node
    agent = REGISTRY[agent_name]

    start = time.monotonic()
    result = agent.execute(context)
    duration_ms = int((time.monotonic() - start) * 1000)

    validation = agent.validate(result)
    if not validation.valid:
        result = AgentResult(
            status="failure",
            error=f"validation failed: {validation.violations}",
            retryable=True,
        )
    return result, duration_ms


def _persist_agent_result(
    db: Session,
    run: WorkflowRun,
    context: WorkflowContext,
    node: str,
    agent_name: str,
    result: AgentResult,
    duration_ms: int,
) -> None:
    for artifact_type in result.output_artifacts:
        if artifact_type in context.artifacts:
            save_artifact(
                db,
                workflow_id=run.id,
                artifact_type=artifact_type,
                content=context.artifacts[artifact_type],
                created_by=agent_name,
            )

    _log_event(
        db,
        run,
        agent=agent_name,
        stage=node,
        event_type="stage_success" if result.status == "success" else "stage_failure",
        decision="; ".join(result.decisions) if result.decisions else None,
        reason=result.error,
        duration_ms=duration_ms,
        output_artifacts=result.output_artifacts,
    )
    if result.status != "success":
        run.failure_count += 1
        db.commit()


def _invoke_agent(
    db: Session, run: WorkflowRun, context: WorkflowContext, node: str, agent_name: str
) -> AgentResult:
    result, duration_ms = _execute_agent(context, node, agent_name)
    _persist_agent_result(db, run, context, node, agent_name, result, duration_ms)
    return result


def _run_parallel_branch(
    db: Session, run: WorkflowRun, context: WorkflowContext
) -> tuple[AgentResult, AgentResult]:
    """ORCH-09 / ADR-010: IMPLEMENTATION and TEST_DESIGN genuinely run
    concurrently, each against its own flags copy (so setting "stage" on one
    thread can't race with the other) but sharing the same context.artifacts
    dict (each writes a different key, so no write conflict). All DB writes
    happen afterward, sequentially, on the caller's own session."""

    def compute(stage: str, agent_name: str) -> tuple[AgentResult, int]:
        thread_context = context.model_copy()
        thread_context.flags = dict(context.flags)
        return _execute_agent(thread_context, stage, agent_name)

    with ThreadPoolExecutor(max_workers=2) as pool:
        impl_future = pool.submit(compute, "IMPLEMENTATION", "development")
        test_future = pool.submit(compute, "TEST_DESIGN", "test")
        impl_result, impl_duration = impl_future.result()
        test_result, test_duration = test_future.result()

    _persist_agent_result(
        db, run, context, "IMPLEMENTATION", "development", impl_result, impl_duration
    )
    _persist_agent_result(db, run, context, "TEST_DESIGN", "test", test_result, test_duration)
    _log_event(db, run, agent=None, stage="JOIN", event_type="stage_success")
    return impl_result, test_result


def run_until_pause(db: Session, run: WorkflowRun, context: WorkflowContext) -> WorkflowRun:
    """Executes graph nodes starting at run.current_stage until a human gate is
    pending, the workflow completes, or it stops (safe-stop/rejected/failed).
    Synchronous and resumable (ADR-009) - callers persist state, exit, and can
    call this again later to continue from exactly where it left off."""
    while True:
        node = run.current_stage

        if graph.is_terminal(node):
            if run.status not in state.TERMINAL_STATUSES:
                run.status = state.STAGE_TO_STATUS[node]
            if node == "COMPLETE" and run.completed_at is None:
                run.completed_at = utc_now()
                run.status = "COMPLETED"
            db.commit()
            return run

        spec = graph.NODES[node]

        if "gate" in spec:
            gate = spec["gate"]
            if approvals.is_rejected(db, run.id, gate):
                run.status = "REJECTED"
                db.commit()
                return run
            if not approvals.is_approved(db, run.id, gate):
                run.status = state.STAGE_TO_STATUS[node]
                db.commit()
                _log_event(db, run, agent=None, stage=node, event_type="gate_pending")
                return run
            run.current_stage = graph.next_nodes(node)[0]
            run.status = state.STAGE_TO_STATUS[run.current_stage]
            db.commit()
            continue

        if node == "IMPLEMENTATION":
            impl_result, test_result = _run_parallel_branch(db, run, context)
            failed = next((r for r in (impl_result, test_result) if r.status != "success"), None)
            if failed is not None:
                context.flags["_last_failure_retryable"] = failed.retryable
                run.current_stage = "RETRY_EVALUATION" if failed.retryable else "SAFE_STOP"
            else:
                run.current_stage = "TEST_EXECUTION"  # graph.next_node("JOIN")
            run.status = state.STAGE_TO_STATUS[run.current_stage]
            db.commit()
            continue

        if node == "TEST_EXECUTION":
            result = _invoke_agent(db, run, context, node, "test")
            context.flags["_last_failure_retryable"] = result.retryable
            outcome = "pass" if result.status == "success" else "fail"
            run.current_stage = graph.next_node(node, outcome)
            run.status = state.STAGE_TO_STATUS[run.current_stage]
            db.commit()
            continue

        if node == "SECURITY_REVIEW":
            result = _invoke_agent(db, run, context, node, "security_review")
            if result.status == "success":
                outcome = "pass"
            elif not result.retryable:
                outcome = "critical"
            else:
                outcome = "non_critical"
            context.flags["_last_failure_retryable"] = result.retryable
            run.current_stage = graph.next_node(node, outcome)
            run.status = state.STAGE_TO_STATUS[run.current_stage]
            db.commit()
            continue

        if node == "RETRY_EVALUATION":
            retryable = context.flags.get("_last_failure_retryable", False)
            outcome = retry.evaluate_retry(run, retryable)
            _log_event(
                db,
                run,
                agent=None,
                stage=node,
                event_type="retry" if outcome == "retry" else "stage_failure",
                reason=outcome,
            )
            run.current_stage = graph.next_node(node, outcome)
            run.status = state.STAGE_TO_STATUS[run.current_stage]
            db.commit()
            continue

        if node == "ROLLBACK":
            rollback.rollback(db, run)  # sets status=SAFE_STOPPED, current_stage=SAFE_STOP
            _log_event(db, run, agent=None, stage=node, event_type="rollback")
            continue

        if node in _SIMPLE_AGENT_NODES:
            agent_name = spec.get("agent")
            if agent_name is None:
                run.current_stage = graph.next_node(node)
                run.status = state.STAGE_TO_STATUS[run.current_stage]
                db.commit()
                continue
            result = _invoke_agent(db, run, context, node, agent_name)
            if result.status != "success":
                run.status = "FAILED"
                db.commit()
                return run
            run.current_stage = graph.next_node(node)
            run.status = state.STAGE_TO_STATUS[run.current_stage]
            db.commit()
            continue

        raise AssertionError(f"unhandled node in orchestrator: {node}")  # pragma: no cover
