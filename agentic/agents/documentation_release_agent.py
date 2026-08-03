"""Documentation & Release Agent - deterministic mode.
docs/architecture/ai-dlc-design.md #4.7."""

from typing import ClassVar

from agentic.agents.base import AgentResult, ValidationResult, default_validate
from agentic.context import WorkflowContext
from agentic.schemas import ReleaseOutput, SecurityReviewOutput


class DocumentationReleaseAgent:
    name = "documentation_release"
    allowed_tools: ClassVar[list[str]] = []
    prohibited_actions: ClassVar[list[str]] = ["claim_release_ready_without_gate3_evidence"]

    def execute(self, context: WorkflowContext) -> AgentResult:
        security_review: SecurityReviewOutput | None = context.artifacts.get("security_review")
        if security_review is None:
            return AgentResult(
                status="failure", error="missing security_review artifact", retryable=True
            )

        output = ReleaseOutput(
            doc_sections=["README", "REVIEWER_GUIDE", "AI_USAGE", "SECURITY", "CHANGELOG"],
            release_readiness_summary=(
                f"scenario={context.scenario_type}; "
                f"security_recommendation={security_review.release_recommendation}"
            ),
            known_limitations=[
                "Deterministic agents use fixed rule sets, not general NLU (ADR-004)",
                "In-process concurrency stands in for true parallelism (ADR-010)",
            ],
            production_backlog=[
                "Split app/orchestration databases",
                "Real live-LLM tool allowlisting if that mode is built (ADR-011)",
            ],
        )
        context.artifacts["release"] = output
        return AgentResult(
            status="success",
            output_artifacts=["release"],
            decisions=["produced release-readiness artifact"],
            requires_approval=True,  # Gate 3
        )

    def validate(self, result: AgentResult) -> ValidationResult:
        return default_validate(result)
