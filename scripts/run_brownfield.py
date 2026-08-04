#!/usr/bin/env python
"""Brownfield scenario runner - SCEN-02. Enhances the greenfield baseline with
configurable expiry + disable tracking, and demonstrates dependency-aware
replanning (ORCH-10) against that baseline - the master brief's own worked
example (detailed-technical-design.md #13): "expires after 30 days" (fixed)
-> "configurable 1-365 days".

The greenfield baseline is reconstructed deterministically (via
RequirementAnalysisAgent.analyze_greenfield(), the exact same rule set a real
prior greenfield run would have produced) rather than requiring a live prior
workflow run to exist - so this scenario is runnable standalone, in any order.

Usage:
  python scripts/run_brownfield.py
  python scripts/run_brownfield.py --auto-approve-demo
  python scripts/run_brownfield.py --workflow-id <id>
"""

import argparse
import sys

from _scenario_common import advance, load_or_start, next_action_hint, write_evidence

from agentic.agents.requirement_analysis_agent import RequirementAnalysisAgent
from agentic.replanning import compute_replan
from app.database.session import SessionLocal

RAW_REQUIREMENT = (
    "Enhance the existing URL shortener to support configurable expiry "
    "(1-365 days) and disabling of links without breaking existing links."
)


def _demonstrate_replanning(context) -> None:
    """compute_replan() detects added/removed requirement IDs via symmetric
    difference - it has no way to detect "FR-05's definition changed" from an
    ID-list-only data model (IDs are plain strings, not objects carrying their
    own content). So the master brief's worked example - FR-05 changing from
    fixed-30-days to configurable-1-365 - is represented the same way the
    dedicated unit test (tests/orchestration/test_replanning.py) already
    represents it: the baseline plus an explicit marker ID for what changed,
    not a literal diff of this scenario's own (deliberately narrow) requirement
    output against the baseline."""
    baseline = RequirementAnalysisAgent().analyze_greenfield(
        "Build a URL-shortener service that creates short URLs, redirects users, "
        "records privacy-conscious analytics, and handles invalid input safely."
    )
    revised = baseline.model_copy(deep=True)
    revised.functional_requirements = [
        *baseline.functional_requirements,
        "FR-05-CONFIGURABLE-EXPIRY",
    ]

    result = compute_replan(
        baseline, revised, existing_artifact_types=set(context.artifacts.keys())
    )

    print("--- Dynamic replanning demonstration (ORCH-10) ---")
    print(f"Changed/added requirement IDs: {sorted(result.changed_ids)}")
    print(f"Stale artifact types:          {sorted(result.stale)}")
    print(f"Preserved artifact types:      {sorted(result.preserved)}")
    print(
        "(finer-grained preservation lives at the file level, not the artifact_type "
        "level - see docs/architecture/detailed-technical-design.md #13: this "
        "scenario's DevelopmentOutput.changed_files only ever lists app/config.py "
        "and app/services/expiry.py, never app/services/url_safety.py or "
        "app/api/health.py, which is where 'short-code generation and the health "
        "endpoint are untouched' is actually demonstrated.)"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--auto-approve-demo", action="store_true")
    parser.add_argument("--workflow-id", default=None)
    parser.add_argument("--inject-failure", default=None)
    parser.add_argument("--inject-permanent-failure", action="store_true")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        run, context = load_or_start(
            db,
            scenario_type="brownfield",
            raw_requirement=RAW_REQUIREMENT,
            workflow_id=args.workflow_id,
        )
        if args.inject_failure:
            context.flags["inject_failure"] = args.inject_failure
        if args.inject_permanent_failure:
            context.flags["inject_permanent_failure"] = True

        run = advance(db, run, context, auto_approve_demo=args.auto_approve_demo)

        if "requirement" in context.artifacts:
            _demonstrate_replanning(context)

        write_evidence(run)
        print(next_action_hint(run, "run_brownfield.py"))
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
