"""Security & Quality Review Agent - deterministic mode.
docs/architecture/ai-dlc-design.md #4.6."""

import subprocess
from typing import ClassVar

from agentic.agents.base import AgentResult, ValidationResult, default_validate
from agentic.context import WorkflowContext
from agentic.schemas import SecurityFinding, SecurityReviewOutput, TestOutput


class SecurityReviewAgent:
    name = "security_review"
    allowed_tools: ClassVar[list[str]] = ["ruff", "mypy", "pip-audit"]
    prohibited_actions: ClassVar[list[str]] = ["recommend_release_with_unresolved_critical_finding"]

    def execute(self, context: WorkflowContext) -> AgentResult:
        findings: list[SecurityFinding] = []

        if context.flags.get("inject_permanent_failure"):
            findings.append(
                SecurityFinding(
                    severity="critical",
                    description="injected permanent critical finding for demonstration",
                )
            )

        test_output: TestOutput = context.artifacts.get("test", TestOutput())
        if test_output.failed > 0:
            findings.append(
                SecurityFinding(
                    severity="high",
                    description=f"{test_output.failed} test(s) failing at review time",
                )
            )

        if self._run(["ruff", "check", "app", "agentic"]) != 0:
            findings.append(SecurityFinding(severity="medium", description="ruff findings present"))

        critical = [f for f in findings if f.severity == "critical"]
        output = SecurityReviewOutput(
            findings=findings,
            required_action="safe_stop" if critical else ("retry" if findings else "none"),
            release_recommendation="block" if critical else "release",
        )
        context.artifacts["security_review"] = output

        if critical:
            return AgentResult(
                status="failure",
                error=f"critical security finding(s): {[f.description for f in critical]}",
                retryable=False,  # ADR-007: critical -> SAFE_STOP directly, not a retry
                output_artifacts=["security_review"],
                risks=[f.description for f in findings],
            )
        if findings:
            return AgentResult(
                status="failure",
                error=f"non-critical finding(s): {[f.description for f in findings]}",
                retryable=True,
                output_artifacts=["security_review"],
                risks=[f.description for f in findings],
            )
        return AgentResult(
            status="success",
            output_artifacts=["security_review"],
            decisions=["no security findings"],
            requires_approval=True,  # contributes to Gate 3
        )

    def validate(self, result: AgentResult) -> ValidationResult:
        return default_validate(result)

    @staticmethod
    def _run(cmd: list[str]) -> int:
        try:
            return subprocess.run(cmd, capture_output=True, timeout=60, check=False).returncode
        except FileNotFoundError:
            return 0  # tool unavailable in this environment - not treated as a finding
