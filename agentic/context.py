from typing import Any, Literal

from pydantic import BaseModel, Field

ScenarioType = Literal["greenfield", "brownfield", "ambiguous"]


class WorkflowContext(BaseModel):
    """Carried through every stage of one workflow run. Agents read prior-stage
    output from `artifacts` (keyed by artifact_type) and, as a side effect of
    execute(), write their own output back into `artifacts` under their own
    artifact_type - the AgentResult they return only carries IDs/metadata for
    logging, not the content itself, matching the common contract in
    docs/architecture/ai-dlc-design.md #2 exactly."""

    model_config = {"arbitrary_types_allowed": True}

    workflow_id: str
    scenario_type: ScenarioType
    raw_requirement: str
    correlation_id: str
    artifacts: dict[str, Any] = Field(default_factory=dict)
    flags: dict[str, Any] = Field(default_factory=dict)  # e.g. failure-injection flags for tests
