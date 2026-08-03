"""Planning Agent - deterministic mode. docs/architecture/ai-dlc-design.md #4.2."""

from typing import ClassVar

from agentic.agents.base import AgentResult, ValidationResult, default_validate
from agentic.context import WorkflowContext
from agentic.schemas import PlanOutput, PlanTask, RequirementAnalysisOutput


class PlanningAgent:
    name = "planning"
    allowed_tools: ClassVar[list[str]] = []
    prohibited_actions: ClassVar[list[str]] = ["invent_task_not_traceable_to_approved_requirement"]

    def execute(self, context: WorkflowContext) -> AgentResult:
        requirement: RequirementAnalysisOutput = context.artifacts["requirement"]
        all_ids = requirement.functional_requirements + requirement.non_functional_requirements

        tasks = [
            PlanTask(id=f"impl-{rid}", description=f"Implement {rid}", parallelizable=True)
            for rid in all_ids
        ] + [
            PlanTask(
                id=f"test-{rid}",
                description=f"Test {rid}",
                depends_on=[f"impl-{rid}"],
                parallelizable=True,
            )
            for rid in all_ids
        ]

        # Self-check (ORCH-05 domain-specific coverage, not a generic schema check):
        # every approved requirement ID must be covered by at least one task.
        covered = {t.id.split("-", 1)[1] for t in tasks}
        missing = [rid for rid in all_ids if rid not in covered]
        if missing:
            return AgentResult(
                status="failure",
                error=f"plan does not cover requirement IDs: {missing}",
                retryable=True,
            )

        output = PlanOutput(
            tasks=tasks,
            validation_checkpoints=["pytest tests/ green", "ruff/mypy clean"],
            definition_of_done=["All approved requirement IDs covered by >=1 task"],
        )
        context.artifacts["plan"] = output

        return AgentResult(
            status="success",
            output_artifacts=["plan"],
            decisions=[f"decomposed {len(all_ids)} requirement IDs into {len(tasks)} tasks"],
            metrics={"task_count": float(len(tasks))},
        )

    def validate(self, result: AgentResult) -> ValidationResult:
        return default_validate(result)
