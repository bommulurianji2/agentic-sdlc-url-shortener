from unittest.mock import patch

from agentic.agents import REGISTRY
from agentic.context import WorkflowContext
from agentic.schemas import SecurityReviewOutput


def _context(scenario_type: str, raw_requirement: str = "test requirement") -> WorkflowContext:
    return WorkflowContext(
        workflow_id="wf-test",
        scenario_type=scenario_type,
        raw_requirement=raw_requirement,
        correlation_id="corr-test",
    )


def test_requirement_analysis_greenfield_produces_all_frs():
    ctx = _context("greenfield")
    result = REGISTRY["requirement_analysis"].execute(ctx)
    assert result.status == "success"
    assert result.requires_approval is True
    assert len(ctx.artifacts["requirement"].functional_requirements) == 8


def test_requirement_analysis_ambiguous_produces_at_least_five_interpretations():
    ctx = _context("ambiguous", "Make shortened links more secure")
    result = REGISTRY["requirement_analysis"].execute(ctx)
    assert result.status == "success"
    assert len(ctx.artifacts["requirement"].ambiguities) >= 5


def test_requirement_analysis_brownfield_targets_expiry_and_disable():
    ctx = _context("brownfield")
    REGISTRY["requirement_analysis"].execute(ctx)
    assert ctx.artifacts["requirement"].functional_requirements == ["FR-05", "FR-06"]


def test_planning_covers_every_requirement_id():
    ctx = _context("greenfield")
    REGISTRY["requirement_analysis"].execute(ctx)
    result = REGISTRY["planning"].execute(ctx)
    assert result.status == "success"

    requirement = ctx.artifacts["requirement"]
    all_ids = set(requirement.functional_requirements + requirement.non_functional_requirements)
    covered = {t.id.split("-", 1)[1] for t in ctx.artifacts["plan"].tasks}
    assert all_ids == covered


def test_architecture_produces_adrs_and_passes_denylist():
    ctx = _context("greenfield")
    REGISTRY["requirement_analysis"].execute(ctx)
    REGISTRY["planning"].execute(ctx)
    result = REGISTRY["architecture"].execute(ctx)
    assert result.status == "success"
    assert ctx.artifacts["architecture"].adrs


def test_development_greenfield_records_change_not_scripted_patch():
    ctx = _context("greenfield")
    result = REGISTRY["development"].execute(ctx)
    assert result.status == "success"
    assert ctx.artifacts["development"].mode == "record_change"


def test_development_brownfield_applies_scripted_patch():
    ctx = _context("brownfield")
    REGISTRY["development"].execute(ctx)
    assert ctx.artifacts["development"].mode == "apply_scripted_patch"
    assert "app/config.py" in ctx.artifacts["development"].changed_files


def test_development_ambiguous_only_adds_rate_limiting():
    ctx = _context("ambiguous")
    REGISTRY["development"].execute(ctx)
    assert ctx.artifacts["development"].changed_files == ["app/api/middleware/rate_limit.py"]


def test_test_agent_design_stage_covers_every_requirement_id():
    ctx = _context("greenfield")
    ctx.flags["stage"] = "TEST_DESIGN"
    REGISTRY["requirement_analysis"].execute(ctx)
    result = REGISTRY["test"].execute(ctx)
    assert result.status == "success"
    designed_ids = {c.requirement_id for c in ctx.artifacts["test"].test_design}
    requirement = ctx.artifacts["requirement"]
    expected_ids = set(
        requirement.functional_requirements + requirement.non_functional_requirements
    )
    assert designed_ids == expected_ids


def test_test_agent_injected_failure_is_retryable():
    ctx = _context("greenfield")
    ctx.flags["stage"] = "TEST_EXECUTION"
    ctx.flags["inject_failure"] = "test_execution"
    result = REGISTRY["test"].execute(ctx)
    assert result.status == "failure"
    assert result.retryable is True


@patch("agentic.agents.test_agent.subprocess.run")
def test_test_agent_execution_parses_pytest_output(mock_run):
    mock_run.return_value.stdout = "42 passed in 1.23s"
    ctx = _context("greenfield")
    ctx.flags["stage"] = "TEST_EXECUTION"
    result = REGISTRY["test"].execute(ctx)
    assert result.status == "success"
    assert ctx.artifacts["test"].passed == 42
    assert ctx.artifacts["test"].failed == 0


def test_security_review_injected_critical_finding_is_not_retryable():
    ctx = _context("greenfield")
    ctx.flags["inject_permanent_failure"] = True
    result = REGISTRY["security_review"].execute(ctx)
    assert result.status == "failure"
    assert result.retryable is False  # ADR-007: critical -> SAFE_STOP directly


@patch("agentic.agents.security_review_agent.subprocess.run")
def test_security_review_clean_run_succeeds(mock_run):
    mock_run.return_value.returncode = 0
    ctx = _context("greenfield")
    result = REGISTRY["security_review"].execute(ctx)
    assert result.status == "success"
    assert result.requires_approval is True


def test_documentation_release_requires_security_review_artifact():
    ctx = _context("greenfield")
    result = REGISTRY["documentation_release"].execute(ctx)
    assert result.status == "failure"


def test_documentation_release_produces_release_artifact():
    ctx = _context("greenfield")
    ctx.artifacts["security_review"] = SecurityReviewOutput(release_recommendation="release")
    result = REGISTRY["documentation_release"].execute(ctx)
    assert result.status == "success"
    assert result.requires_approval is True
