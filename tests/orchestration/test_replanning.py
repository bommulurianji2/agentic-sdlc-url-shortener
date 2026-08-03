from agentic.replanning import ALL_ARTIFACT_TYPES, compute_replan
from agentic.schemas import RequirementAnalysisOutput


def _requirement(non_functional_requirements):
    return RequirementAnalysisOutput(
        normalized_requirement="Short links expire after 30 days.",
        functional_requirements=["FR-01", "FR-02"],
        non_functional_requirements=non_functional_requirements,
    )


def test_no_change_preserves_every_existing_artifact():
    old = _requirement(["NFR-01"])
    new = _requirement(["NFR-01"])  # identical
    result = compute_replan(old, new, ALL_ARTIFACT_TYPES)
    assert result.changed_ids == set()
    assert result.stale == set()
    assert result.preserved == ALL_ARTIFACT_TYPES


def test_expiry_configurability_change_marks_downstream_artifacts_stale():
    """The master brief's own dynamic-replanning worked example: 'expires after
    30 days' (fixed) -> 'configurable 1-365 days'. See detailed-technical-design.md
    #13 - this is deliberately the same change as the brownfield scenario (SCEN-02),
    not a separate throwaway example."""
    old = _requirement(["NFR-01"])
    new = _requirement(["NFR-01", "FR-05-CONFIGURABLE-EXPIRY"])  # the changed/added ID

    existing = {"requirement", "plan", "architecture", "development", "test", "release"}
    result = compute_replan(old, new, existing)

    assert "FR-05-CONFIGURABLE-EXPIRY" in result.changed_ids
    assert result.stale == existing  # every existing artifact_type is re-derived
    assert result.preserved == set()  # at artifact_type granularity - see module docstring


def test_replan_only_touches_artifact_types_that_exist_yet():
    """A run that hasn't reached DOCUMENTATION yet has no 'release' artifact -
    there's nothing to mark stale or preserved that was never produced."""
    old = _requirement([])
    new = _requirement(["NFR-09"])
    existing = {"requirement", "plan"}  # early in the run
    result = compute_replan(old, new, existing)
    assert result.stale == existing
    assert "release" not in result.stale
    assert "release" not in result.preserved
