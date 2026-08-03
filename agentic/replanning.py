"""Dependency-aware replanning - ORCH-10. docs/architecture/detailed-technical-design.md #13.

Replanning here operates at artifact_type granularity - the granularity the
`artifacts` table actually supports (requirement/plan/architecture/development/
test/security_review/release). When a requirement ID genuinely changes, every
downstream artifact_type is honestly re-derived at that granularity - this
module does not pretend to preserve a whole artifact_type when its source
requirement changed. The finer-grained preservation the master brief's worked
example describes (short-code generation untouched, only expiry logic changed)
shows up inside the regenerated development artifact's own changed_files /
impacted_modules list instead - see the brownfield path in
agentic/agents/development_agent.py, which only ever touches app/config.py and
app/services/expiry.py, never app/services/url_safety.py or app/api/health.py."""

from dataclasses import dataclass, field

from agentic.schemas import RequirementAnalysisOutput

ALL_ARTIFACT_TYPES = {
    "requirement",
    "plan",
    "architecture",
    "development",
    "test",
    "security_review",
    "release",
}

DOWNSTREAM_OF_REQUIREMENT = ALL_ARTIFACT_TYPES - {"requirement"}


@dataclass
class ReplanResult:
    changed_ids: set[str] = field(default_factory=set)
    stale: set[str] = field(default_factory=set)
    preserved: set[str] = field(default_factory=set)


def diff_requirement_ids(
    old: RequirementAnalysisOutput, new: RequirementAnalysisOutput
) -> set[str]:
    old_ids = set(old.functional_requirements + old.non_functional_requirements)
    new_ids = set(new.functional_requirements + new.non_functional_requirements)
    return old_ids ^ new_ids  # symmetric difference: added or removed either way


def compute_replan(
    old: RequirementAnalysisOutput,
    new: RequirementAnalysisOutput,
    existing_artifact_types: set[str],
) -> ReplanResult:
    """existing_artifact_types = artifact types actually produced so far for this
    run - a run that hasn't reached DOCUMENTATION yet has no 'release' artifact,
    so there is nothing to mark stale or preserved that was never produced."""
    changed_ids = diff_requirement_ids(old, new)
    if not changed_ids:
        return ReplanResult(preserved=set(existing_artifact_types))

    stale = (DOWNSTREAM_OF_REQUIREMENT | {"requirement"}) & existing_artifact_types
    preserved = existing_artifact_types - stale
    return ReplanResult(changed_ids=changed_ids, stale=stale, preserved=preserved)
