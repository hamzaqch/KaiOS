#!/usr/bin/env python3
"""Rank Python functions by risk: branching complexity against test presence.

Complexity is an approximation of cyclomatic complexity counted from the AST
(decision points plus one). Test presence is a proxy: does any test file mention
the function's name. The score borrows the CRAP shape, so a simple function with
no test stays quiet while a branchy untested one rises to the top.

    score = complexity ** 2 + complexity   when no test mentions it
    score = complexity                     when a test mentions it

Exit codes: 0 clean, 1 a threshold was exceeded or a file could not be parsed,
2 usage.
"""

import argparse
import ast
import json
import os
import sys

DECISION_NODES = (
    ast.If,
    ast.For,
    ast.AsyncFor,
    ast.While,
    ast.ExceptHandler,
    ast.IfExp,
    ast.Assert,
)


def is_test_path(path):
    base = os.path.basename(path)
    if base.startswith("test_") or base.endswith("_test.py"):
        return True
    parts = os.path.normpath(path).split(os.sep)
    return "tests" in parts or "test" in parts


def iter_python_files(targets):
    for target in targets:
        if os.path.isfile(target) and target.endswith(".py"):
            yield target
            continue
        for root, dirs, files in os.walk(target):
            dirs[:] = [
                d
                for d in dirs
                if d not in {".git", "__pycache__", ".venv", "venv", "node_modules"}
            ]
            for filename in sorted(files):
                if filename.endswith(".py"):
                    yield os.path.join(root, filename)


def complexity_of(node):
    """Decision points plus one, ignoring nested function bodies."""
    score = 1
    nested = {
        child
        for child in ast.walk(node)
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child is not node
    }
    nested_nodes = set()
    for inner in nested:
        for child in ast.walk(inner):
            nested_nodes.add(id(child))
    for child in ast.walk(node):
        if id(child) in nested_nodes or child is node:
            continue
        if isinstance(child, DECISION_NODES):
            score += 1
        elif isinstance(child, ast.BoolOp):
            score += max(0, len(child.values) - 1)
        elif isinstance(child, ast.comprehension):
            score += 1 + len(child.ifs)
        elif isinstance(child, ast.Try) and child.orelse:
            score += 1
        elif hasattr(ast, "match_case") and isinstance(child, ast.match_case):
            score += 1
    return score


def collect_functions(path, parse_errors):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            source = handle.read()
    except OSError as exc:
        parse_errors.append({"path": path, "error": str(exc)})
        return []
    try:
        tree = ast.parse(source, filename=path)
    except SyntaxError as exc:
        parse_errors.append({"path": path, "error": "syntax: %s" % exc})
        return []
    found = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            found.append(
                {
                    "path": path,
                    "name": node.name,
                    "line": node.lineno,
                    "complexity": complexity_of(node),
                    "lines": (getattr(node, "end_lineno", node.lineno) or node.lineno)
                    - node.lineno
                    + 1,
                }
            )
    return found


def test_mentions(test_files):
    names = {}
    for path in test_files:
        try:
            with open(path, "r", encoding="utf-8") as handle:
                text = handle.read()
        except OSError:
            continue
        names[path] = text
    return names


def score_functions(functions, test_text, ignore_private):
    rows = []
    for item in functions:
        if ignore_private and item["name"].startswith("_") and not item["name"].startswith("__"):
            continue
        mentioned_in = [
            path for path, text in test_text.items() if item["name"] in text
        ]
        complexity = item["complexity"]
        score = complexity if mentioned_in else complexity * complexity + complexity
        row = dict(item)
        row["tested"] = bool(mentioned_in)
        row["test_files"] = len(mentioned_in)
        row["score"] = score
        rows.append(row)
    rows.sort(key=lambda r: (-r["score"], r["path"], r["line"]))
    return rows


def render(rows, limit, parse_errors):
    lines = [
        "%-6s %-5s %-6s %-26s %s" % ("SCORE", "CPLX", "TESTED", "FUNCTION", "LOCATION"),
        "-" * 76,
    ]
    for row in rows[:limit]:
        lines.append(
            "%-6d %-5d %-6s %-26s %s:%d"
            % (
                row["score"],
                row["complexity"],
                "yes" if row["tested"] else "NO",
                row["name"][:26],
                row["path"],
                row["line"],
            )
        )
    lines.append("-" * 76)
    lines.append("%d functions scored, showing %d" % (len(rows), min(limit, len(rows))))
    untested = [r for r in rows if not r["tested"]]
    lines.append(
        "%d functions have no test mentioning them by name" % len(untested)
    )
    for error in parse_errors:
        lines.append("parse error: %s: %s" % (error["path"], error["error"]))
    return "\n".join(lines)


def build_parser():
    parser = argparse.ArgumentParser(
        prog="hotspots.py",
        description="Rank Python functions by branching complexity against test presence.",
    )
    parser.add_argument("targets", nargs="+", help="files or directories to score")
    parser.add_argument(
        "--tests",
        action="append",
        default=[],
        help="extra directory of tests to scan for name mentions (repeatable)",
    )
    parser.add_argument("--limit", type=int, default=25, help="rows to print (default 25)")
    parser.add_argument(
        "--fail-over",
        type=int,
        default=0,
        help="exit 1 when any function scores above this value",
    )
    parser.add_argument(
        "--include-private",
        action="store_true",
        help="score single-underscore functions too",
    )
    parser.add_argument("--json", action="store_true", help="emit the report as JSON")
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    all_files = list(iter_python_files(args.targets))
    extra = list(iter_python_files(args.tests)) if args.tests else []
    test_files = [p for p in all_files if is_test_path(p)] + extra
    source_files = [p for p in all_files if not is_test_path(p)]
    if not source_files:
        message = "no non-test python files found"
        print(json.dumps({"error": message}) if args.json else "error: %s" % message)
        return 2

    parse_errors = []
    functions = []
    for path in source_files:
        functions.extend(collect_functions(path, parse_errors))
    rows = score_functions(functions, test_mentions(test_files), not args.include_private)

    if args.json:
        print(
            json.dumps(
                {
                    "functions": rows,
                    "counts": {
                        "source_files": len(source_files),
                        "test_files": len(test_files),
                        "functions": len(rows),
                        "untested": sum(1 for r in rows if not r["tested"]),
                    },
                    "parse_errors": parse_errors,
                },
                indent=2,
            )
        )
    else:
        print(render(rows, args.limit, parse_errors))

    if parse_errors:
        return 1
    if args.fail_over and rows and rows[0]["score"] > args.fail_over:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
