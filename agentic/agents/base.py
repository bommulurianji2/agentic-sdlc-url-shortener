"""Common agent contract - docs/architecture/ai-dlc-design.md #2."""

from typing import Literal, Protocol, runtime_checkable

from pydantic import BaseModel, Field

from agentic.context import WorkflowContext


class AgentResult(BaseModel):
    status: Literal["success", "failure", "partial"]
    output_artifacts: list[str] = Field(default_factory=list)
    decisions: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    retryable: bool = False
    requires_approval: bool = False
    metrics: dict[str, float] = Field(default_factory=dict)
    error: str | None = None


class ValidationResult(BaseModel):
    valid: bool
    violations: list[str] = Field(default_factory=list)


@runtime_checkable
class Agent(Protocol):
    name: str

    def execute(self, context: WorkflowContext) -> AgentResult: ...

    def validate(self, result: AgentResult) -> ValidationResult: ...


def default_validate(result: AgentResult) -> ValidationResult:
    """Uniform post-check shared by every agent (ORCH-05). Domain-specific
    checks (requirement-ID coverage, architecture denylist, skipped-test
    policy) run as self-checks inside each agent's own execute(), since they
    need the agent's own working data, not just the returned AgentResult."""
    violations: list[str] = []
    if result.status == "success" and not result.output_artifacts:
        violations.append("a successful result must produce at least one output artifact")
    if result.status == "failure" and not result.error:
        violations.append("a failure result must include an error message")
    return ValidationResult(valid=not violations, violations=violations)
