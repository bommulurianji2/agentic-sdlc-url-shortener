# ADR-009: Synchronous, resumable CLI execution — no background daemon

**Status:** Accepted

**Context:** ORCH-06 requires the orchestrator to be stateful and resumable. A gate pause (e.g. `WAITING_FOR_REQUIREMENT_APPROVAL`) has to actually stop and later continue exactly where it left off.

**Decision:** A scenario script runs the orchestrator loop synchronously in the foreground. Reaching a gate persists `workflow_runs.status`/`current_stage` and the script exits normally (exit code 0, not an error) with that state saved. `scripts/approve_gate.py` records the approval separately. Re-running the scenario script re-loads persisted state from the database and continues from the next unexecuted node.

**Alternatives considered:**
- A long-running worker/daemon process that polls for approvals and resumes automatically — would demonstrate "statefulness" just as well, but adds a background process the reviewer has to know is running, adds a way for the demo to silently be in a broken state (daemon crashed vs./approval genuinely pending), and isn't needed since nothing in the required reviewer flow (§23) depends on automatic resumption without a reviewer action.

**Consequences:** Resuming a workflow always requires an explicit script invocation (this is a feature, not a limitation, for reviewer clarity — "nothing happens until you run something"), but it does mean the orchestrator's resume logic must be exercised by tests as its own concern (load persisted state → continue from correct node), not just tested as "run start-to-finish in one process lifetime."
