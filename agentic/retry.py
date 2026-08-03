"""Bounded retry - GOV-02. docs/architecture/detailed-technical-design.md #11."""

from typing import Literal

from agentic.models import WorkflowRun

MAX_RETRIES = 2


def evaluate_retry(run: WorkflowRun, retryable: bool) -> Literal["retry", "exhausted"]:
    """A retry always re-invokes the same failing stage with the same context
    plus the recorded failure reason - never silently retried with no record
    of what changed (that record is the caller's job, via workflow_events)."""
    current = run.retry_count or 0  # SQLAlchemy defaults apply at INSERT, not construction
    if not retryable or current >= MAX_RETRIES:
        return "exhausted"
    run.retry_count = current + 1
    return "retry"
