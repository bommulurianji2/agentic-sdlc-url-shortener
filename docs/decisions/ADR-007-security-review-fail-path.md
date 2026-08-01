# ADR-007: Added a SECURITY_REVIEW fail-path missing from the source workflow diagram

**Status:** Accepted (reviewer-confirmed)

**Context:** The master brief's §9 workflow diagram draws `SECURITY_REVIEW → DOCUMENTATION` with no fail branch. Its §12, in the same document, requires "critical security validation fails" to trigger `SAFE_STOPPED`, and §7.7 says the Security & Quality Review Agent's output includes a "release recommendation" — implying it can in fact block release. These two parts of the source spec are inconsistent with each other.

**Decision:** Implement the graph with the fail path the governance section requires, not the diagram as literally drawn: a critical finding routes `SECURITY_REVIEW → SAFE_STOP`; a non-critical finding routes into the existing `RETRY_EVALUATION` path (same bounded-retry policy as a test failure — GOV-02).

**Alternatives considered:**
- Implement the diagram literally (security review can only recommend, never block) — rejected by the reviewer when this gap was raised explicitly; it would make GOV-05's "critical security check fails → safe stop" requirement unimplementable, since nothing in the graph would ever route there from a security finding.

**Consequences:** The as-built graph deviates from the master brief's literal diagram in exactly this one place. This ADR exists so that deviation is visible and intentional, not mistaken for an implementation bug.
