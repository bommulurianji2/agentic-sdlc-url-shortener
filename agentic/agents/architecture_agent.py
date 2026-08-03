"""Architecture Agent - deterministic mode. docs/architecture/ai-dlc-design.md #4.3.

For this project's own greenfield scenario, docs/architecture/architecture-overview.md
+ the 12 ADRs are the literal worked example of what this agent produces at
prototype scale, written by Claude Code standing in for the deterministic agent."""

from typing import ClassVar

from agentic.agents.base import AgentResult, ValidationResult, default_validate
from agentic.context import WorkflowContext
from agentic.policies import check_architecture_denylist
from agentic.schemas import ArchitectureOutput


class ArchitectureAgent:
    name = "architecture"
    allowed_tools: ClassVar[list[str]] = []
    prohibited_actions: ClassVar[list[str]] = ["introduce_denylisted_component"]

    def execute(self, context: WorkflowContext) -> AgentResult:
        output = ArchitectureOutput(
            components=[
                "app/api",
                "app/services",
                "app/repositories",
                "agentic/orchestrator",
                "agentic/agents",
            ],
            api_design="REST, /api/v1/urls + bare /{short_code} redirect, single error envelope",
            data_model=(
                "short_urls, click_events, workflow_runs, workflow_events, artifacts, approvals"
            ),
            security_design=(
                "scheme allowlist + SSRF blocking (NFR-01), secrets via env only (GOV-06)"
            ),
            workflow_design="stateful dependency graph, one parallel branch, three human gates",
            adrs=["ADR-001", "ADR-002", "ADR-003", "ADR-005", "ADR-007"],
            production_evolution_path=(
                "split app/orchestration DBs; move to Postgres if scale requires"
            ),
        )

        # Self-check (GOV-06 as code): reject anything referencing a denylisted component.
        combined_text = " ".join(
            [
                output.api_design,
                output.data_model,
                output.security_design,
                output.workflow_design,
                *output.components,
            ]
        )
        violations = check_architecture_denylist(combined_text)
        if violations:
            return AgentResult(
                status="failure",
                error=f"architecture references denylisted components: {violations}",
                retryable=True,
            )

        context.artifacts["architecture"] = output
        return AgentResult(
            status="success",
            output_artifacts=["architecture"],
            decisions=["produced component/API/data/security/workflow design"],
            requires_approval=True,  # contributes to Gate 2
        )

    def validate(self, result: AgentResult) -> ValidationResult:
        return default_validate(result)
