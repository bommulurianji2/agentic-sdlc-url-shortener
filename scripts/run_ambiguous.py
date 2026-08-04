#!/usr/bin/env python
"""Ambiguous scenario runner - SCEN-03. Submits "make shortened links more
secure" and demonstrates the ambiguity-analysis + human-clarification flow
before any implementation happens.

The approved interpretation (requirements-baseline.md SCEN-03): block unsafe
URL schemes, block private-network destinations, use secure random codes,
add basic rate limiting, defer authentication. Four of those five are
already satisfied by the existing greenfield baseline (NFR-01/02) - rate
limiting is the only net-new control this scenario's Development Agent adds
(see build-plan.md task 23's note on why re-implementing the rest would be
worse engineering, not better governance).

Usage:
  python scripts/run_ambiguous.py
  python scripts/run_ambiguous.py --auto-approve-demo
  python scripts/run_ambiguous.py --workflow-id <id>
"""

import argparse
import sys

from _scenario_common import advance, load_or_start, next_action_hint, write_evidence

from app.database.session import SessionLocal

RAW_REQUIREMENT = "Make shortened links more secure."


def _print_ambiguity_analysis(context) -> None:
    requirement = context.artifacts.get("requirement")
    if requirement is None or not requirement.ambiguities:
        return
    print("--- Ambiguity analysis (SCEN-03) ---")
    print(f"{len(requirement.ambiguities)} candidate interpretations identified:")
    for i, item in enumerate(requirement.ambiguities, 1):
        print(f"  {i}. {item}")
    print(
        "Approved interpretation (requirements-baseline.md SCEN-03): block unsafe "
        "schemes + private-network destinations + secure random codes (already "
        "satisfied by the greenfield baseline) + add basic rate limiting (the one "
        "net-new control) - authentication is explicitly deferred."
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
            scenario_type="ambiguous",
            raw_requirement=RAW_REQUIREMENT,
            workflow_id=args.workflow_id,
        )
        if args.inject_failure:
            context.flags["inject_failure"] = args.inject_failure
        if args.inject_permanent_failure:
            context.flags["inject_permanent_failure"] = True

        run = advance(db, run, context, auto_approve_demo=args.auto_approve_demo)

        _print_ambiguity_analysis(context)
        write_evidence(run)
        print(next_action_hint(run, "run_ambiguous.py"))
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
