#!/usr/bin/env python3
"""Summarise a unified diff: per-file churn, test coverage of the change, and
added lines that carry a known risk signal.

Reads a patch file or standard input, so it works on ``git diff`` output, a
``.patch`` from a pull request, or a saved review artefact. It reports; it makes
no judgement about whether the change should merge.

Exit codes: 0 no risk signals, 1 risk signals present, 2 usage or unreadable input.
"""

import argparse
import json
import os
import re
import sys

FILE_HEADER = re.compile(r"^diff --git a/(?P<a>.+?) b/(?P<b>.+)$")
OLD_PATH = re.compile(r"^--- (?:a/)?(?P<path>.+?)(?:\t.*)?$")
NEW_PATH = re.compile(r"^\+\+\+ (?:b/)?(?P<path>.+?)(?:\t.*)?$")
HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+\d+(?:,\d+)? @@")

# Each signal: name, severity, pattern applied to ADDED lines only.
SIGNALS = (
    ("swallowed-exception", "high", re.compile(r"except[^:]*:\s*(pass|return\s*(None)?)\s*$")),
    ("bare-except", "high", re.compile(r"except\s*:")),
    ("shell-interpretation", "high", re.compile(r"shell\s*=\s*True")),
    ("destructive-shell", "high", re.compile(r"rm\s+-rf|Remove-Item\s+-Recurse\s+-Force")),
    ("destructive-sql", "high", re.compile(r"\b(DROP|TRUNCATE)\s+(TABLE|SCHEMA|DATABASE)\b", re.IGNORECASE)),
    ("force-push", "high", re.compile(r"push\s+.*--force")),
    ("hardcoded-credential", "high", re.compile(r"(password|secret|token|api[_-]?key)\s*[:=]\s*[\"'][^\"']{6,}", re.IGNORECASE)),
    ("silent-default", "medium", re.compile(r"\.get\([^)]*,\s*(None|\"\"|''|0)\s*\)\s*(or|#|$)")),
    ("broad-catch-log-only", "medium", re.compile(r"except\s+Exception[^:]*:\s*$")),
    ("todo-left", "medium", re.compile(r"\b(TODO|FIXME|XXX|HACK)\b")),
    ("debug-print", "medium", re.compile(r"^\s*(print\(|console\.log\(|Write-Host\s)")),
    ("sleep-as-sync", "medium", re.compile(r"(time\.sleep\(|Start-Sleep)")),
    ("type-escape", "low", re.compile(r"(#\s*type:\s*ignore|:\s*Any\b|as\s+any\b)")),
    ("commented-code", "low", re.compile(r"^\s*#\s*(if|for|while|def|return|import)\s")),
)

TEST_HINTS = ("test_", "_test.", "tests/", "/test/", "spec.", ".spec.")
DOC_EXT = (".md", ".rst", ".txt")
SOURCE_EXT = (".py", ".ps1", ".ts", ".js", ".sql", ".java", ".cs", ".go", ".rb", ".scala")


def is_test(path):
    lowered = path.replace("\\", "/").lower()
    return any(hint in lowered for hint in TEST_HINTS)


def classify(path):
    lowered = path.lower()
    if is_test(path):
        return "test"
    if lowered.endswith(DOC_EXT):
        return "doc"
    if lowered.endswith((".json", ".yaml", ".yml", ".toml", ".ini", ".cfg")):
        return "config"
    if lowered.endswith(SOURCE_EXT):
        return "source"
    return "other"


def parse(text):
    files = []
    current = None
    signals = []
    for lineno, raw in enumerate(text.splitlines(), start=1):
        header = FILE_HEADER.match(raw)
        if header:
            current = {
                "path": header.group("b"),
                "old_path": header.group("a"),
                "added": 0,
                "removed": 0,
                "hunks": 0,
                "binary": False,
                "status": "modified",
            }
            files.append(current)
            continue
        if current is None:
            if raw.startswith("--- ") or raw.startswith("+++ "):
                match = NEW_PATH.match(raw) or OLD_PATH.match(raw)
                if match:
                    current = {
                        "path": match.group("path"),
                        "old_path": match.group("path"),
                        "added": 0,
                        "removed": 0,
                        "hunks": 0,
                        "binary": False,
                        "status": "modified",
                    }
                    files.append(current)
            continue
        if raw.startswith("new file mode"):
            current["status"] = "added"
            continue
        if raw.startswith("deleted file mode"):
            current["status"] = "deleted"
            continue
        if raw.startswith("rename from") or raw.startswith("rename to"):
            current["status"] = "renamed"
            continue
        if raw.startswith("Binary files") or raw.startswith("GIT binary patch"):
            current["binary"] = True
            continue
        if HUNK.match(raw):
            current["hunks"] += 1
            continue
        if raw.startswith("+++") or raw.startswith("---"):
            match = NEW_PATH.match(raw)
            if match and match.group("path") not in ("/dev/null",):
                current["path"] = match.group("path")
            continue
        if raw.startswith("+"):
            current["added"] += 1
            body = raw[1:]
            for name, severity, pattern in SIGNALS:
                if pattern.search(body):
                    signals.append(
                        {
                            "signal": name,
                            "severity": severity,
                            "path": current["path"],
                            "patch_line": lineno,
                            "text": body.strip()[:140],
                        }
                    )
        elif raw.startswith("-"):
            current["removed"] += 1
    for item in files:
        item["kind"] = classify(item["path"])
        item["churn"] = item["added"] + item["removed"]
    return files, signals


def coverage_gaps(files):
    """Source directories changed with no test file changed anywhere."""
    changed_source = [f for f in files if f["kind"] == "source" and f["churn"] > 0]
    changed_tests = [f for f in files if f["kind"] == "test" and f["churn"] > 0]
    if not changed_source:
        return []
    if changed_tests:
        return []
    return [
        {"path": f["path"], "churn": f["churn"]}
        for f in sorted(changed_source, key=lambda x: -x["churn"])
    ]


def summarise(files, signals):
    by_kind = {}
    for item in files:
        bucket = by_kind.setdefault(item["kind"], {"files": 0, "added": 0, "removed": 0})
        bucket["files"] += 1
        bucket["added"] += item["added"]
        bucket["removed"] += item["removed"]
    severities = {"high": 0, "medium": 0, "low": 0}
    for item in signals:
        severities[item["severity"]] += 1
    return {
        "files": len(files),
        "added": sum(f["added"] for f in files),
        "removed": sum(f["removed"] for f in files),
        "by_kind": by_kind,
        "severities": severities,
        "test_gap": coverage_gaps(files),
    }


def render(files, signals, summary, top):
    lines = [
        "%-46s %-7s %6s %6s %5s" % ("FILE", "KIND", "+", "-", "HUNKS"),
        "-" * 76,
    ]
    for item in sorted(files, key=lambda f: -f["churn"])[:top]:
        path = item["path"]
        if len(path) > 46:
            path = "..." + path[-43:]
        lines.append(
            "%-46s %-7s %6d %6d %5d"
            % (path, item["kind"], item["added"], item["removed"], item["hunks"])
        )
    if len(files) > top:
        lines.append("... %d more files" % (len(files) - top))
    lines.append("-" * 76)
    lines.append(
        "%d files, +%d -%d   high %d  medium %d  low %d"
        % (
            summary["files"],
            summary["added"],
            summary["removed"],
            summary["severities"]["high"],
            summary["severities"]["medium"],
            summary["severities"]["low"],
        )
    )
    if summary["test_gap"]:
        lines.append("")
        lines.append("NO TEST FILE CHANGED, source files touched:")
        for item in summary["test_gap"][:top]:
            lines.append("  %s (+/- %d)" % (item["path"], item["churn"]))
    if signals:
        lines.append("")
        lines.append("RISK SIGNALS IN ADDED LINES:")
        order = {"high": 0, "medium": 1, "low": 2}
        for item in sorted(signals, key=lambda s: (order[s["severity"]], s["path"])):
            lines.append(
                "  %-6s %-22s %s"
                % (item["severity"].upper(), item["signal"], item["path"])
            )
            lines.append("         %s" % item["text"])
    else:
        lines.append("")
        lines.append("RISK SIGNALS: none matched.")
    return "\n".join(lines)


def build_parser():
    parser = argparse.ArgumentParser(
        prog="diff_stats.py",
        description="Summarise churn, test coverage and risk signals in a unified diff.",
    )
    parser.add_argument(
        "patch", nargs="?", default="-", help="patch file, or - for standard input"
    )
    parser.add_argument("--top", type=int, default=20, help="rows to print (default 20)")
    parser.add_argument("--json", action="store_true", help="emit the report as JSON")
    parser.add_argument(
        "--min-severity",
        choices=["high", "medium", "low"],
        default="low",
        help="ignore signals below this severity",
    )
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.patch == "-":
            text = sys.stdin.read()
        else:
            if not os.path.isfile(args.patch):
                raise OSError("no such file")
            with open(args.patch, "r", encoding="utf-8", errors="replace") as handle:
                text = handle.read()
    except OSError as exc:
        payload = {"error": "cannot read patch", "path": args.patch, "detail": str(exc)}
        print(json.dumps(payload) if args.json else "error: %s" % exc)
        return 2
    if not text.strip():
        payload = {"error": "empty patch"}
        print(json.dumps(payload) if args.json else "error: empty patch")
        return 2

    files, signals = parse(text)
    floor = {"high": 0, "medium": 1, "low": 2}[args.min_severity]
    order = {"high": 0, "medium": 1, "low": 2}
    signals = [s for s in signals if order[s["severity"]] <= floor]
    summary = summarise(files, signals)
    if args.json:
        print(
            json.dumps(
                {"summary": summary, "files": files, "signals": signals}, indent=2
            )
        )
    else:
        print(render(files, signals, summary, args.top))
    return 1 if signals else 0


if __name__ == "__main__":
    sys.exit(main())
