"""Requirement Analysis Agent - deterministic mode.
See docs/architecture/ai-dlc-design.md #4.1.

Applies a fixed rule set tuned to this project's three known scenarios, not
general-purpose natural-language understanding - a documented limitation
(ADR-004), not a hidden one."""

from typing import ClassVar

from agentic.agents.base import AgentResult, ValidationResult, default_validate
from agentic.context import WorkflowContext
from agentic.schemas import RequirementAnalysisOutput


class RequirementAnalysisAgent:
    name = "requirement_analysis"
    allowed_tools: ClassVar[list[str]] = []
    prohibited_actions: ClassVar[list[str]] = [
        "self_approve_gate",
        "proceed_past_unresolved_ambiguity",
    ]

    def execute(self, context: WorkflowContext) -> AgentResult:
        if context.scenario_type == "ambiguous":
            output = self.analyze_ambiguous(context.raw_requirement)
        elif context.scenario_type == "brownfield":
            output = self.analyze_brownfield(context.raw_requirement)
        else:
            output = self.analyze_greenfield(context.raw_requirement)

        context.artifacts["requirement"] = output

        return AgentResult(
            status="success",
            output_artifacts=["requirement"],
            decisions=[f"normalized requirement for scenario={context.scenario_type}"],
            risks=output.risks,
            retryable=False,
            requires_approval=True,  # Gate 1 is always required (GOV-01)
            metrics={"ambiguities_found": float(len(output.ambiguities))},
        )

    def validate(self, result: AgentResult) -> ValidationResult:
        return default_validate(result)

    def analyze_greenfield(self, raw: str) -> RequirementAnalysisOutput:
        """Public: reused directly by scripts/run_brownfield.py to reconstruct
        the greenfield baseline for the ORCH-10 replanning demonstration,
        without depending on a prior live workflow run having been executed."""
        return RequirementAnalysisOutput(
            normalized_requirement=(
                "Build a URL-shortener service that creates short URLs, redirects "
                "users, records privacy-conscious analytics, and handles invalid "
                "input safely."
            ),
            functional_requirements=[
                "FR-01",
                "FR-02",
                "FR-03",
                "FR-04",
                "FR-05",
                "FR-06",
                "FR-07",
                "FR-08",
            ],
            non_functional_requirements=[
                "NFR-01",
                "NFR-02",
                "NFR-03",
                "NFR-04",
                "NFR-05",
                "NFR-06",
                "NFR-07",
                "NFR-08",
                "NFR-09",
            ],
            ambiguities=[],
            assumptions=[
                "Expiry defaults to 30 days fixed if not provided "
                "(detailed-technical-design.md #2)."
            ],
            scope=[
                "Create/redirect/inspect/analytics/expire/disable/custom-alias",
                "URL safety controls",
            ],
            out_of_scope=["Authentication", "Rate limiting", "Hard delete", "Custom frontend"],
            acceptance_criteria=[
                "All FR-01-FR-08 implemented and tested",
                "docker compose up --build serves /health with no API key",
            ],
            risks=["SSRF allowlist/denylist logic is easy to get subtly wrong"],
        )

    def analyze_brownfield(self, raw: str) -> RequirementAnalysisOutput:
        return RequirementAnalysisOutput(
            normalized_requirement=(
                "Enhance the existing URL shortener to support configurable "
                "expiry (1-365 days) and disabling of links without breaking "
                "existing links."
            ),
            functional_requirements=["FR-05", "FR-06"],
            non_functional_requirements=[],
            ambiguities=[],
            assumptions=[
                "Existing links created under the fixed 30-day default remain "
                "valid and unaffected by the migration."
            ],
            scope=[
                "Configurable expires_in_days (1-365)",
                "Refactor expiry logic into app/services/expiry.py",
            ],
            out_of_scope=["Changing the redirect/analytics contracts"],
            acceptance_criteria=[
                "Existing short_urls rows still redirect correctly after migration",
                "expires_in_days validated to 1-365",
            ],
            risks=["A non-additive migration could break existing links"],
        )

    def analyze_ambiguous(self, raw: str) -> RequirementAnalysisOutput:
        return RequirementAnalysisOutput(
            normalized_requirement=raw,
            functional_requirements=[],
            non_functional_requirements=[],
            ambiguities=[
                "Stronger short-code generation",
                "Malicious URL blocking",
                "SSRF controls",
                "Expiry enforcement",
                "Authentication",
                "Rate limiting",
                "Ownership of links",
                "Abuse reporting",
            ],
            assumptions=[],
            scope=[],
            out_of_scope=[],
            acceptance_criteria=[],
            risks=[
                "Proceeding without clarifying which interpretation is approved "
                "risks building the wrong control"
            ],
        )
