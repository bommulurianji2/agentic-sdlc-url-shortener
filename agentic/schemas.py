"""Per-agent output schemas - docs/architecture/ai-dlc-design.md #4.
Every agent I/O boundary is a typed Pydantic model, never a bare dict
(coding standard, detailed-technical-design.md #14)."""

from pydantic import BaseModel, Field


class RequirementAnalysisOutput(BaseModel):
    normalized_requirement: str
    functional_requirements: list[str] = Field(default_factory=list)
    non_functional_requirements: list[str] = Field(default_factory=list)
    ambiguities: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    scope: list[str] = Field(default_factory=list)
    out_of_scope: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)


class PlanTask(BaseModel):
    id: str
    description: str
    depends_on: list[str] = Field(default_factory=list)
    parallelizable: bool = False
    priority: str = "P0"


class PlanOutput(BaseModel):
    tasks: list[PlanTask] = Field(default_factory=list)
    validation_checkpoints: list[str] = Field(default_factory=list)
    definition_of_done: list[str] = Field(default_factory=list)


class ArchitectureOutput(BaseModel):
    components: list[str] = Field(default_factory=list)
    api_design: str = ""
    data_model: str = ""
    security_design: str = ""
    workflow_design: str = ""
    adrs: list[str] = Field(default_factory=list)
    production_evolution_path: str = ""


class DevelopmentOutput(BaseModel):
    mode: str  # "record_change" | "apply_scripted_patch" - ADR-012
    changed_files: list[str] = Field(default_factory=list)
    migration_scripts: list[str] = Field(default_factory=list)
    change_summary: str = ""
    impacted_modules: list[str] = Field(default_factory=list)
    self_review_result: str = "clean"


class PlannedTestCase(BaseModel):
    requirement_id: str
    name: str


class TestOutput(BaseModel):
    test_design: list[PlannedTestCase] = Field(default_factory=list)
    passed: int = 0
    failed: int = 0
    skipped: list[str] = Field(default_factory=list)
    failure_details: list[str] = Field(default_factory=list)
    retry_recommendation: str | None = None


class SecurityFinding(BaseModel):
    severity: str  # critical | high | medium | low
    description: str


class SecurityReviewOutput(BaseModel):
    findings: list[SecurityFinding] = Field(default_factory=list)
    required_action: str = "none"
    release_recommendation: str = "release"  # "release" | "block"


class ReleaseOutput(BaseModel):
    doc_sections: list[str] = Field(default_factory=list)
    release_readiness_summary: str = ""
    known_limitations: list[str] = Field(default_factory=list)
    production_backlog: list[str] = Field(default_factory=list)
