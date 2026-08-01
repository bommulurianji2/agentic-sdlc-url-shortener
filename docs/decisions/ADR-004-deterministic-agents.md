# ADR-004: Deterministic agents by default; live LLM is an optional pluggable provider

**Status:** Accepted

**Context:** Binding assumptions §3.12/§3.13 require deterministic, offline-capable execution that never needs an API key, while allowing an optional live-LLM mode.

**Decision:** Every agent (`agentic/agents/*.py`) implements its logic as deterministic, rule-based/templated Python — normalizing requirements, generating plans, producing designs, etc., using fixed logic rather than a model call. An `agentic/llm_provider.py` module defines the interface an agent *could* call for a live-LLM-generated output, selected by an environment variable, defaulting to absent/off.

**Alternatives considered:**
- LLM-first with a deterministic "mock mode" fallback — inverts the actual requirement (deterministic must be the fully-functional default, not a degraded fallback) and risks the reviewer path silently depending on network access.

**Consequences:** Deterministic agent outputs are necessarily more templated/rule-based than what a real LLM would produce (e.g. the Requirement Analysis Agent's "ambiguity list" for the ambiguous scenario is a curated, fixed list rather than freshly reasoned) — this is called out as a known limitation (SUBMIT-05), not hidden.
