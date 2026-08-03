"""Test Agent - deterministic mode. docs/architecture/ai-dlc-design.md #4.5.

Handles both the TEST_DESIGN and TEST_EXECUTION graph nodes (both map to this
one agent, per graph.py). The orchestrator sets context.flags["stage"] to the
current node name before calling execute(), so one agent instance can behave
differently per node while the orchestrator still calls every agent uniformly.
Test execution is literally running pytest and parsing the result - no
generative/deterministic-rule ambiguity here at all."""

import re
import subprocess
from typing import ClassVar

from agentic.agents.base import AgentResult, ValidationResult, default_validate
from agentic.context import WorkflowContext
from agentic.policies import check_no_skipped_tests
from agentic.schemas import PlannedTestCase, RequirementAnalysisOutput, TestOutput


class TestAgent:
    name = "test"
    allowed_tools: ClassVar[list[str]] = ["pytest"]
    prohibited_actions: ClassVar[list[str]] = [
        "mark_failing_suite_as_passing",
        "skip_test_to_force_pass",
    ]

    def execute(self, context: WorkflowContext) -> AgentResult:
        if context.flags.get("stage") == "TEST_DESIGN":
            return self._design(context)
        return self._run_tests(context)

    def validate(self, result: AgentResult) -> ValidationResult:
        return default_validate(result)

    def _design(self, context: WorkflowContext) -> AgentResult:
        requirement: RequirementAnalysisOutput = context.artifacts["requirement"]
        all_ids = requirement.functional_requirements + requirement.non_functional_requirements
        cases = [PlannedTestCase(requirement_id=rid, name=f"test_{rid.lower()}") for rid in all_ids]
        existing: TestOutput = context.artifacts.get("test", TestOutput())
        existing.test_design = cases
        context.artifacts["test"] = existing
        return AgentResult(
            status="success",
            output_artifacts=["test"],
            decisions=[f"designed {len(cases)} planned test cases (one per requirement ID)"],
            metrics={"planned_case_count": float(len(cases))},
        )

    def _run_tests(self, context: WorkflowContext) -> AgentResult:
        injected = context.flags.get("inject_failure")
        if injected == "test_execution":
            existing = context.artifacts.get("test", TestOutput())
            existing.failed = 1
            existing.failure_details = ["injected failure for demonstration purposes"]
            existing.retry_recommendation = "retry"
            context.artifacts["test"] = existing
            return AgentResult(
                status="failure",
                error="injected test failure at test_execution",
                retryable=True,
                output_artifacts=["test"],
            )

        result = subprocess.run(
            ["pytest", "tests/", "--tb=no", "-q"],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        passed, failed = self._parse_pytest_summary(result.stdout)
        skipped: list[str] = []
        violations = check_no_skipped_tests(skipped)

        existing = context.artifacts.get("test", TestOutput())
        existing.passed = passed
        existing.failed = failed
        existing.skipped = skipped
        context.artifacts["test"] = existing

        if failed > 0 or violations:
            reason = f"{failed} test(s) failed"
            if violations:
                reason += f"; policy violations: {violations}"
            return AgentResult(
                status="failure", error=reason, retryable=True, output_artifacts=["test"]
            )

        return AgentResult(
            status="success",
            output_artifacts=["test"],
            decisions=[f"{passed} tests passed, 0 failed"],
            metrics={"passed": float(passed), "failed": float(failed)},
        )

    @staticmethod
    def _parse_pytest_summary(stdout: str) -> tuple[int, int]:
        passed_match = re.search(r"(\d+) passed", stdout)
        failed_match = re.search(r"(\d+) failed", stdout)
        return (
            int(passed_match.group(1)) if passed_match else 0,
            int(failed_match.group(1)) if failed_match else 0,
        )
