#!/usr/bin/env python
"""Greenfield scenario runner - SCEN-01. Drives the full graph for the initial
URL-shortener build.

Usage:
  python scripts/run_greenfield.py                       # pauses for real approval at each gate
  python scripts/run_greenfield.py --auto-approve-demo    # demo mode only - never the default
  python scripts/run_greenfield.py --workflow-id <id>      # resume a paused run
  python scripts/run_greenfield.py --inject-failure test_execution
  python scripts/run_greenfield.py --inject-permanent-failure
"""

import argparse
import sys

from _scenario_common import advance, load_or_start, next_action_hint, write_evidence

from app.database.session import SessionLocal

RAW_REQUIREMENT = (
    "Build a URL-shortener service that creates short URLs, redirects users, "
    "records privacy-conscious analytics, and handles invalid input safely."
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
            scenario_type="greenfield",
            raw_requirement=RAW_REQUIREMENT,
            workflow_id=args.workflow_id,
        )
        if args.inject_failure:
            context.flags["inject_failure"] = args.inject_failure
        if args.inject_permanent_failure:
            context.flags["inject_permanent_failure"] = True

        run = advance(db, run, context, auto_approve_demo=args.auto_approve_demo)
        write_evidence(run)
        print(next_action_hint(run, "run_greenfield.py"))
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
