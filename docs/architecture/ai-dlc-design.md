# AI-DLC / Agent Design — Phase 4

**Status:** DRAFT — feeds into Gate 2 (formal, after Phase 6)
**Input:** requirements-baseline.md v3, architecture-overview.md, ADR-001…ADR-012

---

## 1. Why Agents Are Used

Not because an LLM can write code faster — because the assessment's actual subject is a **governed process**: a requirement should move through distinct, accountable stages (analysis → plan → design → build → test → review → release), each producing an inspectable artifact, each independently retryable/rollback-able, with humans owning the three material approval decisions. Splitting this into 7 single-responsibility agents behind one contract is what makes retry/rollback/replanning meaningful at a *stage* granularity rather than an all-or-nothing script — you can retry the Test Agent's output without re-running Requirement Analysis.

No RAG: nothing in this system needs retrieval over a document corpus — every agent's input is already the exact, small, structured context it needs (the prior stage's artifact). Adding a vector store would be pure overhead, consistent with the "do not overengineer" list.

## 2. Common Agent Contract

```python
class AgentResult(BaseModel):
    status: Literal["success", "failure", "partial"]
    output_artifacts: list[str]       # artifact IDs written via artifact_store
    decisions: list[str]              # human-readable decision log lines -> workflow_events
    risks: list[str]
    retryable: bool
    requires_approval: bool
    metrics: dict[str, float]          # e.g. {"duration_seconds": 1.2}
    error: str | None = None

class ValidationResult(BaseModel):
    valid: bool
    violations: list[str]

class Agent(Protocol):
    name: str
    allowed_tools: list[str]          # empty for every agent in deterministic mode - see ADR-011
    prohibited_actions: list[str]

    def execute(self, context: WorkflowContext) -> AgentResult: ...
    def validate(self, result: AgentResult) -> ValidationResult: ...
```

`orchestrator.py` calls `execute()`, then always calls `validate()` before accepting the result — this is ORCH-05 as executable code, not a convention. A `validate()` failure is treated as a formatting-class failure (retryable per GOV-02) unless the agent's own `retryable=False`.

## 3. Deterministic Mode vs. Optional LLM Mode

Every agent's primary implementation is deterministic (rule-based/templated Python), selected by `AGENT_MODE=deterministic` (default). An `AGENT_MODE=llm` path exists as a thin, optional layer behind `agentic/llm_provider.py`; it is never required to satisfy any requirement in this project (ADR-004).

### 3.1 Prompt boundaries (apply only if LLM mode is ever enabled)

- Prompts are fixed templates per agent, not freely composed strings — reduces injection surface and keeps outputs schema-shaped.
- A prompt receives only the specific `WorkflowContext` fields that agent's contract lists as Inputs below — never the full context object, never environment variables, never other workflow runs' data.
- No secret, credential, or `.env` value is ever interpolated into a prompt (GOV-06).

### 3.2 Hallucination controls

1. Every agent output is validated against a strict Pydantic schema before acceptance (§4 below) — a shape mismatch is rejected outright, not coerced.
2. Planning/Architecture agents' `validate()` checks **requirement-ID coverage**: every FR/NFR/ORCH/GOV/TRACE/METRIC/SCEN ID in the approved requirement must appear in the output; an agent can't silently invent IDs not in scope, or drop ones that are.
3. Architecture Agent output is checked against a denylist of banned components (Kubernetes, service mesh, event streaming, vector DB, etc.) — turns the "do not overengineer" convention into an automated policy check (`policies.py`).
4. The ambiguous scenario's candidate-interpretation list is validated against a minimum count (≥5) and a closed vocabulary, not accepted as free text.
5. Human gates are the final backstop regardless of the above — a schema-valid, ID-complete, policy-compliant output can still be rejected by a human at Gate 1/2/3.

### 3.3 Evaluation

No separate eval harness — `validate()` plus the orchestrator's entry/exit criteria *is* the evaluation mechanism, run on every single invocation, not sampled. This is deliberately simpler than a scoring rubric because deterministic outputs are either schema-correct and ID-complete or they aren't; there's no "quality score" to approximate at this scale.

### 3.4 Feedback and observability

Every `execute()` call, pass or fail, writes one `workflow_events` row (TRACE-02); a retry attempt records what was corrected between attempt N and N+1 in its `decisions` list, so the audit trail shows *why* attempt 2 succeeded where attempt 1 didn't, not just that it did.

## 4. Per-Agent Contracts

### 4.1 Requirement Analysis Agent

| | |
|---|---|
| **Inputs** | raw requirement text, `scenario_type`, prior approved requirement (brownfield/replanning only), binding constraints |
| **Outputs** | `RequirementAnalysisOutput`: normalized_requirement, functional_requirements[], non_functional_requirements[], ambiguities[], assumptions[], scope[], out_of_scope[], acceptance_criteria[], risks[] |
| **Allowed tools** | none — pure computation over provided text + fixed rule tables |
| **Prohibited actions** | cannot self-approve; for the ambiguous scenario, cannot proceed past an unresolved ambiguity without `requires_approval=True` |
| **Entry criteria** | raw requirement present; workflow state `CREATED` or `REPLANNING` |
| **Exit criteria** | output validates against schema; ≥1 acceptance criterion; ambiguities list present (may be empty for greenfield/brownfield, must be ≥5 for the ambiguous scenario per §3.2.4) |
| **Retry eligibility** | retryable on schema-validation failure; not retryable if `scenario_type` is unrecognized (needs a human/dev fix, not a re-run) |
| **Handoff** | → Gate 1 (human) → Planning Agent |
| **Human approval** | **Gate 1** |

**Deterministic-mode limitation, stated plainly:** this agent does not perform open-ended natural-language understanding. It applies a fixed rule set tuned to this project's three known scenario inputs (keyword/category matching against the requirement text). The ambiguous scenario's ≥5 interpretations are a curated, fixed lookup table keyed to the known input phrase, not freshly reasoned ambiguity detection — see ADR-004 and SUBMIT-05 (documented limitation, not hidden).

### 4.2 Planning Agent

| | |
|---|---|
| **Inputs** | Gate-1-approved requirement; prior approved plan (brownfield/replanning) |
| **Outputs** | `PlanOutput`: tasks[] (id, description, depends_on[], parallelizable, priority), validation_checkpoints[], definition_of_done[] |
| **Allowed tools** | read access to the approved requirement and, for brownfield/replanning, the prior plan artifact |
| **Prohibited actions** | cannot introduce a task not traceable to an ID in the Gate-1-approved requirement (no scope creep past what was approved) |
| **Entry criteria** | Gate 1 approved |
| **Exit criteria** | 100% of the approved requirement's IDs are covered by ≥1 task — checked in code by `validate()`, not eyeballed |
| **Retry eligibility** | retryable on coverage-check failure (a completeness/formatting-class failure per GOV-02) |
| **Handoff** | → Architecture Agent (no dedicated gate — matches the graph: `TASK_DECOMPOSITION → ARCHITECTURE_DESIGN` directly) |
| **Human approval** | none directly; its output is inspectable as part of Gate 2's bundle |

### 4.3 Architecture Agent

| | |
|---|---|
| **Inputs** | approved requirement + Planning output; prior approved architecture (brownfield/replanning) |
| **Outputs** | `ArchitectureOutput`: components[], api_design, data_model, security_design, workflow_design, adrs[], production_evolution_path |
| **Allowed tools** | read access to approved requirement, plan, and (brownfield/replanning) prior architecture artifact |
| **Prohibited actions** | output rejected by `policies.py` if it references a denylisted component (K8s, service mesh, event streaming, vector DB/RAG, auth platform, full frontend) |
| **Entry criteria** | Planning output valid |
| **Exit criteria** | covers component/API/data/security/workflow sections; ≥1 ADR per material decision |
| **Retry eligibility** | retryable if a policy check fails (regenerate without violating policy); not retryable if the underlying requirement is self-contradictory (needs Gate 1 revisit, not a re-run) |
| **Handoff** | → informal check-in (this project's own practice) → Planning/Design phases 4-6 → **Gate 2** (formal, bundled with the build plan) |
| **Human approval** | contributes to **Gate 2** |

*This project's own Phase 3 (architecture-overview.md + 12 ADRs) is a literal worked example of this agent's output for the greenfield scenario — written by Claude Code standing in for the deterministic Architecture Agent, at prototype scale.*

### 4.4 Development Agent

| | |
|---|---|
| **Inputs** | Gate-2-approved architecture + build plan |
| **Outputs** | `DevelopmentOutput`: changed_files[], migration_scripts[], change_summary, impacted_modules[], self_review_result |
| **Mode (ADR-012, hybrid)** | **Greenfield:** `record_change()` — links to real commits/diffs already engineered directly; runs ruff/mypy and attaches results as `self_review_result`. **Brownfield/ambiguous:** `apply_scripted_patch()` — genuinely, mechanically applies a pre-modeled, narrow patch (e.g. widen the expiry-range constant, add one Alembic migration, add a scheme/host check) at runtime, then runs the same self-review step. |
| **Allowed tools** | filesystem write restricted to the specific files named in the approved build plan; `ruff`/`mypy` subprocess invocation for self-review |
| **Prohibited actions** | cannot bypass tests; cannot deploy; cannot silently overwrite an already-approved artifact (must version — GOV-07) |
| **Entry criteria** | Gate 2 approved |
| **Exit criteria** | self-review completes without an unhandled exception (lint/type-check may still report findings — those flow to Security & Quality Review, not blocked here) |
| **Retry eligibility** | retryable on a local, correctable defect (GOV-02 example case) |
| **Handoff** | → JOIN (waits for Test Agent's TEST_DESIGN branch) |
| **Human approval** | none directly; feeds Gate 3 evidence |

### 4.5 Test Agent

| | |
|---|---|
| **Inputs** | approved architecture + build plan (runs concurrently with Development Agent, not after it) |
| **Outputs** | `TestOutput`: test_design[] (one planned case per requirement ID — TRACE-03 as generated output), execution_report (pass/fail per test, coverage %), failure_details[], retry_recommendation |
| **Allowed tools** | `pytest` subprocess invocation; read access to source + test files |
| **Prohibited actions** | cannot mark a failing suite as passing; cannot skip/xfail a test to force a pass — a self-check flags any newly-skipped test as a policy violation |
| **Entry criteria** | test design: architecture/build plan approved (parallel with Development). Test execution: JOIN reached (both branches done) |
| **Exit criteria** | a parsed pytest report exists (any outcome) |
| **Retry eligibility** | retryable if failure is a local code defect (GOV-02); bounded at 2 |
| **Handoff** | PASS → Security & Quality Review Agent. FAIL → Retry Evaluation → (retry: Development Agent \| exhausted: Rollback → Safe Stop) |
| **Human approval** | none directly; results are Gate 3 evidence |

### 4.6 Security & Quality Review Agent

| | |
|---|---|
| **Inputs** | implementation + test execution report |
| **Outputs** | `SecurityReviewOutput`: findings[] (severity: critical/high/medium/low), required_action, release_recommendation |
| **Allowed tools** | `ruff`/`mypy`/`pip-audit` subprocess invocation, and the project's own `tests/security` results; read access to logging config (to check for secret-masking) |
| **Prohibited actions** | cannot issue a "release" recommendation while an unresolved critical finding exists |
| **Entry criteria** | TEST_EXECUTION passed |
| **Exit criteria** | findings list produced (possibly empty) with severities assigned |
| **Retry eligibility** | non-critical finding → Retry Evaluation (bounded, same policy as test failure). **Critical finding → Safe Stop directly** (ADR-007's corrected fail-path) |
| **Handoff** | pass → Documentation & Release Agent. Critical fail → Safe Stop. Non-critical fail → Retry Evaluation |
| **Human approval** | contributes to **Gate 3** |

### 4.7 Documentation & Release Agent

| | |
|---|---|
| **Inputs** | every artifact produced so far in this run |
| **Outputs** | `ReleaseOutput`: doc_sections[] (README/REVIEWER_GUIDE/etc. content relevant to this run), release_readiness_summary, known_limitations[], production_backlog[] |
| **Allowed tools** | read-only access to `artifacts/` (aggregation only — it never re-derives facts, only synthesizes from what other agents already recorded) |
| **Prohibited actions** | cannot state a release is ready if the workflow's own status is `SAFE_STOPPED` or any Gate 3 input is missing |
| **Entry criteria** | Security & Quality Review passed (or its retry cycle resolved) |
| **Exit criteria** | release-readiness artifact produced, referencing every upstream artifact's version |
| **Retry eligibility** | retryable on schema/completeness failure |
| **Handoff** | → **Gate 3** → Complete |
| **Human approval** | **Gate 3** |

## 5. Governance Summary (cross-reference)

Every agent above is already subject to GOV-01…07 by construction: none can self-approve a gate (GOV-01), retries are bounded to 2 everywhere they're eligible (GOV-02), deterministic mode *is* the fallback (GOV-03, ADR-004), rollback/safe-stop are orchestrator-level, not agent-level, decisions (GOV-04/05 — no agent decides to roll itself back), the denylist/coverage/skip-test checks above are the concrete GOV-06 guardrails, and GOV-07 (no silent overwrite) is enforced by `artifact_store.py` for every agent's `output_artifacts`, not re-implemented per agent.

---
*Produced by: (meta) this phase's own output doubles as the Planning + Architecture agents' worked example for the "agent design" stage itself — Phase 4 of the SDLC Orchestrator.*
