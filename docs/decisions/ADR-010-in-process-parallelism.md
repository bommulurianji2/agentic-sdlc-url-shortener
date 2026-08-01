# ADR-010: In-process concurrency for the IMPLEMENTATION / TEST_DESIGN parallel branch

**Status:** Accepted

**Context:** ORCH-09 requires independent stages to run concurrently with an explicit join, demonstrated by `IMPLEMENTATION` and `TEST_DESIGN` running in parallel after the architecture gate.

**Decision:** Run both agents concurrently via a `concurrent.futures.ThreadPoolExecutor` inside the single orchestrator process; `orchestrator.py` blocks on both futures (the join) before proceeding to `TEST_EXECUTION`.

**Alternatives considered:**
- Separate OS processes or containers per branch — genuine parallelism, but neither agent does CPU-bound or long-running work in deterministic mode (they're template/rule-based generation, sub-second each), so the isolation benefit doesn't justify the added process-management complexity (spawning, IPC, failure handling across process boundaries) for a prototype.

**Consequences:** This demonstrates *concurrent execution with a synchronization point* faithfully, but is explicitly not the same as production-grade distributed parallelism — called out in architecture-overview.md §10 risks so it isn't oversold to a reviewer as more than it is.
