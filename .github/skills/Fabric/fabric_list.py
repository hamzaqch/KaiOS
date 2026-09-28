#!/usr/bin/env python3
"""List the bundled analysis patterns so an agent can pick one without guessing.

Each pattern is a markdown file under references/patterns/. Its name is the
file stem, its title is the first level-one heading, and its purpose is the
first blockquote line. Standard library only.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DEFAULT_DIR = Path(__file__).resolve().parent / "references" / "patterns"


def read_pattern(path: Path) -> dict:
    title = ""
    purpose = ""
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not title and stripped.startswith("# "):
            title = stripped[2:].strip()
            continue
        if not purpose and stripped.startswith("> "):
            purpose = stripped[2:].strip()
        if title and purpose:
            break
    return {
        "name": path.stem,
        "title": title or path.stem,
        "purpose": purpose,
        "path": str(path),
    }


def load(directory: Path) -> list[dict]:
    if not directory.is_dir():
        return []
    return [read_pattern(p) for p in sorted(directory.glob("*.md"))]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="fabric_list.py",
        description="List or show the bundled analysis patterns.",
    )
    parser.add_argument("pattern", nargs="?", help="print one pattern's full text")
    parser.add_argument("--dir", default=str(DEFAULT_DIR), help="pattern directory")
    parser.add_argument("--json", action="store_true", help="emit JSON")
    args = parser.parse_args(argv)

    directory = Path(args.dir)
    patterns = load(directory)
    if not patterns:
        print("error: no patterns found in {0}".format(directory), file=sys.stderr)
        return 1

    if args.pattern:
        match = next((p for p in patterns if p["name"] == args.pattern), None)
        if match is None:
            names = ", ".join(p["name"] for p in patterns)
            print("error: unknown pattern {0}. known: {1}".format(args.pattern, names), file=sys.stderr)
            return 1
        if args.json:
            body = Path(match["path"]).read_text(encoding="utf-8")
            print(json.dumps(dict(match, body=body), indent=2))
        else:
            print(Path(match["path"]).read_text(encoding="utf-8"))
        return 0

    if args.json:
        print(json.dumps({"count": len(patterns), "patterns": patterns}, indent=2))
    else:
        width = max(len(p["name"]) for p in patterns)
        for pattern in patterns:
            print("{0:<{1}}  {2}".format(pattern["name"], width, pattern["purpose"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
