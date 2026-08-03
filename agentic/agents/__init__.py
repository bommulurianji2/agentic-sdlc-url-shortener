from agentic.agents.architecture_agent import ArchitectureAgent
from agentic.agents.development_agent import DevelopmentAgent
from agentic.agents.documentation_release_agent import DocumentationReleaseAgent
from agentic.agents.planning_agent import PlanningAgent
from agentic.agents.requirement_analysis_agent import RequirementAnalysisAgent
from agentic.agents.security_review_agent import SecurityReviewAgent
from agentic.agents.test_agent import TestAgent

REGISTRY = {
    "requirement_analysis": RequirementAnalysisAgent(),
    "planning": PlanningAgent(),
    "architecture": ArchitectureAgent(),
    "development": DevelopmentAgent(),
    "test": TestAgent(),
    "security_review": SecurityReviewAgent(),
    "documentation_release": DocumentationReleaseAgent(),
}

__all__ = ["REGISTRY"]
