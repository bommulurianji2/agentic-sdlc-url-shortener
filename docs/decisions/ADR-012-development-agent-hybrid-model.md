# ADR-012: Development Agent uses a hybrid model — governed evidence for greenfield, real scripted patches for brownfield/ambiguous

**Status:** Accepted (reviewer-confirmed)

**Context:** §7.5 of the master brief describes the Development Agent producing "source changes" as an autonomous output. Taken fully literally for the greenfield scenario, this would mean deterministically template-generating an entire real FastAPI application at runtime — which isn't meaningfully "deterministic" (a general-purpose code generator is effectively a compiler) and conflicts with binding assumption §3.14 (the greenfield build must become a *stable* baseline for brownfield), since a regenerated-from-template app wouldn't be stable across runs.

**Decision:**
- **Greenfield:** the real application code is engineered directly (by Claude Code, in Phase 7), not synthesized by a template engine at runtime. The Development Agent's `execute()` for this scenario records and links to the real commits/diffs, runs self-review checks (ruff/mypy output), and produces a change summary — it governs and evidences the work rather than authoring it live.
- **Brownfield and ambiguous:** the specific changes are narrow and known in advance (e.g. widen an expiry-range constant, add one Alembic migration, add a scheme/host check). For these, the Development Agent genuinely auto-applies a scripted patch at runtime — real, mechanical code modification, not narration — because the change is scoped tightly enough to template honestly.

**Alternatives considered:**
- Governance-and-evidence for all three scenarios — simplest and safest, but demonstrates zero literal agent-authored code, understating what a deterministic agent can honestly do for a narrow, well-modeled change.
- Full runtime codegen for all three, including the initial app — highest fidelity to §7.5's literal wording, but high implementation risk and very likely lower code quality than direct engineering, for no proportionate benefit in a time-boxed prototype.

**Consequences:** Two different code paths inside the Development Agent (`agentic/agents/development_agent.py`): a `record_change()` path (greenfield) and an `apply_scripted_patch()` path (brownfield/ambiguous), each satisfying GOV-07 (new artifact version, no silent overwrite) and NFR-07 (self-review before hand-off). This is documented explicitly so a reviewer doesn't read the greenfield scenario's Development Agent output and expect the same runtime-codegen behavior for brownfield, or vice versa.
