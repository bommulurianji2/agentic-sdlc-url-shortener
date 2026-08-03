"""Development Agent - hybrid model (ADR-012). docs/architecture/ai-dlc-design.md #4.4."""

import subprocess
from typing import ClassVar

from agentic.agents.base import AgentResult, ValidationResult, default_validate
from agentic.context import WorkflowContext
from agentic.schemas import DevelopmentOutput


class DevelopmentAgent:
    name = "development"
    allowed_tools: ClassVar[list[str]] = ["ruff", "mypy"]
    prohibited_actions: ClassVar[list[str]] = [
        "bypass_tests",
        "deploy",
        "silently_overwrite_approved_artifact",
    ]

    def execute(self, context: WorkflowContext) -> AgentResult:
        if context.scenario_type == "greenfield":
            output = self._record_change()
        elif context.scenario_type == "brownfield":
            output = self._apply_brownfield_patch()
        else:
            output = self._apply_ambiguous_patch()

        context.artifacts["development"] = output
        return AgentResult(
            status="success",
            output_artifacts=["development"],
            decisions=[f"development mode={output.mode}"],
        )

    def validate(self, result: AgentResult) -> ValidationResult:
        return default_validate(result)

    def _record_change(self) -> DevelopmentOutput:
        """Greenfield: the real app code was engineered directly; this agent records
        and self-reviews it rather than authoring it live at runtime (ADR-012)."""
        return DevelopmentOutput(
            mode="record_change",
            changed_files=["app/", "agentic/"],
            migration_scripts=["alembic/versions/*"],
            change_summary="Greenfield URL shortener + orchestration engine, engineered directly.",
            impacted_modules=["app.api", "app.services", "app.repositories", "agentic"],
            self_review_result=self._self_review(["app", "agentic"]),
        )

    def _apply_brownfield_patch(self) -> DevelopmentOutput:
        """Brownfield: a narrow, pre-modeled change, genuinely auto-applied (ADR-012)."""
        return DevelopmentOutput(
            mode="apply_scripted_patch",
            changed_files=["app/config.py", "app/services/expiry.py"],
            migration_scripts=["alembic (expires_in_days support)"],
            change_summary="Widened expiry to configurable 1-365 days; extracted expiry logic.",
            impacted_modules=["app.config", "app.services.expiry", "app.api.urls"],
            self_review_result=self._self_review(["app"]),
        )

    def _apply_ambiguous_patch(self) -> DevelopmentOutput:
        """Ambiguous: rate limiting is the only net-new control (build-plan task 23 note)."""
        return DevelopmentOutput(
            mode="apply_scripted_patch",
            changed_files=["app/api/middleware/rate_limit.py"],
            migration_scripts=[],
            change_summary="Added basic rate limiting - the one net-new control for this scenario.",
            impacted_modules=["app.api.middleware"],
            self_review_result=self._self_review(["app"]),
        )

    def _self_review(self, paths: list[str]) -> str:
        try:
            result = subprocess.run(
                ["ruff", "check", *paths],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            return "clean" if result.returncode == 0 else result.stdout[-500:]
        except FileNotFoundError:
            return "ruff not available in this environment"
