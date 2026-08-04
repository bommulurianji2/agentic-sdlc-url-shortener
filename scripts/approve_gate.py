#!/usr/bin/env python
"""CLI approval tool - GOV-01, ADR-008 (CLI-only; no approval REST endpoint by design).

Usage:
  python scripts/approve_gate.py <workflow_id> <gate> <approved|rejected> \
      [--approver NAME] [--comments "..."]
"""

import argparse
import sys

from agentic import approvals
from app.database.session import SessionLocal


def main() -> int:
    parser = argparse.ArgumentParser(description="Record a human decision at a workflow gate.")
    parser.add_argument("workflow_id")
    parser.add_argument("gate", choices=sorted(approvals.VALID_GATES))
    parser.add_argument("decision", choices=sorted(approvals.VALID_DECISIONS))
    parser.add_argument("--approver", default="reviewer")
    parser.add_argument("--comments", default=None)
    args = parser.parse_args()

    db = SessionLocal()
    try:
        approval = approvals.record_approval(
            db,
            workflow_id=args.workflow_id,
            gate=args.gate,
            approver=args.approver,
            decision=args.decision,
            comments=args.comments,
        )
        # Read attributes while the session is still open - SQLAlchemy expires
        # them on commit, and a lazy reload after db.close() raises
        # DetachedInstanceError.
        timestamp = approval.timestamp
    finally:
        db.close()

    print(
        f"Recorded: workflow={args.workflow_id} gate={args.gate} "
        f"decision={args.decision} approver={args.approver} at {timestamp}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
