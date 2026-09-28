"""``python -m kaios.hooks <Event>``: stdin in, one JSON object out, exit 0.

Rule: this entry point is what the registry and the PowerShell wrapper call, and
it exits 0 on every path so a broken hook can never break a chat session.
Falsifier: any invocation that exits non-zero or writes something other than one
JSON object to stdout.
"""

from __future__ import annotations

import json
import sys

from .runner import run_event


def main(argv: list | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0].startswith("-"):
        sys.stdout.write(json.dumps({"continue": True}, sort_keys=True) + "\n")
        return 0
    return run_event(args[0])


if __name__ == "__main__":
    raise SystemExit(main())
