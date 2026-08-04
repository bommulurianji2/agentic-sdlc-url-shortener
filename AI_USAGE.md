# AI Usage

## Tool

**Claude Code** (Claude Sonnet 5), used as the primary engineering execution assistant across the entire SDLC — requirement analysis through implementation, testing, Docker/CI, and this documentation. Not used: any live LLM inside the *application itself* — every agent in `agentic/agents/` runs in deterministic mode; no API key was used or is required anywhere in the shipped system.

## Where it assisted

Everything, end to end: requirements normalization, architecture design (12 ADRs), the orchestrator/agent implementation, the FastAPI application, all 117 tests, Docker/CI, and this document set. The human (the repository owner) drove direction, made every approval decision, and caught gaps by asking pointed questions rather than accepting output at face value.

## Representative prompts and how they shaped the work

- *"Are you sure we're covering everything from the original assessment?"* (asked twice, in a row) — the first requirements baseline draft only captured the URL-shortener application requirements, missing the orchestration/governance/traceability/metrics/scenario/submission items entirely. Caught by the human re-asking rather than accepting the first "yes." Fixed across two revisions (v1→v2→v3), including a genuine second gap found on the third pass (brownfield scope only covered "enhancement," not the "refactoring or bug fix" the original item also named; "reliability features" had no dedicated requirement).
- *"If you see something illogical, question me"* — led to two things being surfaced rather than silently resolved: Gate 2's timing (the master brief defines it as approving architecture + the implementation plan together, but those don't exist at the same point in the phase sequence — resolved as two touchpoints, one informal, one formal, per the human's choice) and a real inconsistency in the master brief's own workflow diagram (`SECURITY_REVIEW` had no drawn fail-path to `SAFE_STOP`, despite the governance section requiring one) — the human confirmed the fix before it was implemented.
- A direct design question — how literally should the "Development Agent" author code at runtime versus record work done directly — was put to the human as a genuine three-way choice (governance-only, hybrid, full runtime codegen) rather than decided silently, since it materially changed what got built. The human chose the hybrid model, which is what shipped.
- *"Where are you committing my code?"* — surfaced that a target GitHub repo existed but was named for an unrelated purpose; the human chose to rename it rather than use a different one or leave it as-is.

## Accepted vs. corrected output

Accepted largely as generated: the application code, the orchestrator/agent implementation, and the test suite, after each passed its own validation (tests green, ruff/black/mypy clean) before being committed — nothing was committed on faith.

Corrected, because live execution (not just writing the code) surfaced real defects:

- A thread-unsafe shared SQLAlchemy session in the one parallel branch.
- Bare `pytest`/`ruff` subprocess calls that don't resolve via `PATH` outside an activated venv.
- A `DetachedInstanceError` from reading an ORM attribute after closing its session.
- SQLAlchemy column defaults applying at INSERT, not object construction (a `retry_count` was `None`, not `0`, on an unpersisted object).
- Exceptions raised inside `BaseHTTPMiddleware.dispatch()` not reaching FastAPI's registered exception handler — a genuine Starlette limitation, not a bug in the handler.
- The Docker image not `COPY`-ing `tests/` at all, which would have made both the reviewer's required `pytest` command and the agents' own runtime test execution silently see zero tests.
- A real regression bug in the brownfield expiry feature (`expires_in_days` accepted 0/negative/>365 unchecked) — caught by a test written specifically to catch it, before the buggy version was ever committed.

None of these were "the AI got it wrong and a human caught it after the fact" — they were caught by actually running the code (tests, live scenario execution, a real Docker build) rather than trusting that generated code was correct because it looked correct.

## Human decisions (not delegated)

Every Gate 1/2/3 approval in this repository's own construction; the Development Agent's hybrid model; Gate 2's two-touchpoint staging; the `SECURITY_REVIEW` fail-path fix; the GitHub repository's identity (rename vs. new repo) and the timing of every push; and the overall pacing of the build (phase by phase, with explicit go-ahead between phases).

## Security precautions

No secrets, credentials, or `.env` values were ever placed in a prompt or a commit. Every commit was validated (tests + lint + type-check) before being made — the assistant never committed on the assumption that generated code was correct. Destructive git operations (force-push, hard reset, history rewrite) were never used.

## Limitations

Deterministic agents apply a fixed rule set tuned to this project's three known scenarios (see [ADR-004](docs/decisions/ADR-004-deterministic-agents.md)) — they do not perform general-purpose natural-language requirement understanding, and that's stated as a limitation in the requirements baseline itself, not discovered later. Everything else generated (application code, tests, docs) is real, working, and validated — not a mockup.
