"""Governance guardrails - docs/architecture/ai-dlc-design.md #3.2, GOV-06.
Turns the "do not overengineer" convention into an automated check instead
of a review-time judgment call."""

DENYLISTED_COMPONENTS = {
    "kubernetes",
    "k8s",
    "service mesh",
    "istio",
    "linkerd",
    "kafka",
    "rabbitmq",
    "event streaming",
    "message queue",
    "vector database",
    "vector db",
    "rag",
    "pinecone",
    "weaviate",
    "auth platform",
    "oauth provider",
    "full frontend",
    "spa framework",
}


def check_architecture_denylist(architecture_text: str) -> list[str]:
    lowered = architecture_text.lower()
    return sorted(term for term in DENYLISTED_COMPONENTS if term in lowered)


def check_no_skipped_tests(skipped_tests: list[str]) -> list[str]:
    """A newly-skipped/xfailed test is a policy violation, not a pass
    (ai-dlc-design.md #4.5 - the Test Agent cannot skip a test to force one)."""
    return [f"test skipped without prior approval: {name}" for name in skipped_tests]
