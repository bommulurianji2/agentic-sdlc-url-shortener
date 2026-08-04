#!/usr/bin/env python
"""Full demonstration - runs all three scenarios (greenfield, brownfield,
ambiguous) back to back. --auto-approve-demo is required: this script exists
specifically for unattended demonstration, never as the default operating
mode (GOV-01 - auto-approval must never be the default; run each
scripts/run_<scenario>.py individually for the real CLI-approval flow).

Usage:
  python scripts/run_demo.py --auto-approve-demo
"""

import argparse
import subprocess
import sys


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--auto-approve-demo",
        action="store_true",
        required=True,
        help="Required - this script only ever runs in auto-approve demo mode.",
    )
    args = parser.parse_args()
    del args  # only used for the --auto-approve-demo presence/help text above

    scenarios = ["run_greenfield.py", "run_brownfield.py", "run_ambiguous.py"]
    results: dict[str, int] = {}
    for script in scenarios:
        # Flush explicitly: when stdout is redirected to a file (not a tty),
        # Python buffers print() separately from a child subprocess writing
        # directly to the same fd, so headers can appear out of order otherwise.
        print(f"\n{'=' * 20} {script} {'=' * 20}", flush=True)
        result = subprocess.run(
            [sys.executable, f"scripts/{script}", "--auto-approve-demo"], check=False
        )
        results[script] = result.returncode

    print(f"\n{'=' * 20} summary {'=' * 20}")
    for script, code in results.items():
        print(f"{script}: {'ok' if code == 0 else f'FAILED (exit {code})'}")

    return 0 if all(code == 0 for code in results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
