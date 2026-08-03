"""Common agent contract - docs/architecture/ai-dlc-design.md #2."""

from typing import Literal, Protocol

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


class Agent(Protocol):
    name: str
    allowed_tools: list[str]
    prohibited_actions: list[str]

    def execute(self, context: WorkflowContext) -> AgentResult: ...

    def validate(self, result: AgentResult) -> ValidationResult: ...
