#!/usr/bin/env python3
"""Grade model outputs against a case file of typed assertions.

The agent produces the outputs; this tool only grades them, so a grade is
reproducible and cannot be talked out of a verdict.

Inputs are two JSONL files.

cases.jsonl, one object per case::

    {"id": "c1", "suite": "capability", "input": "...",
     "asserts": [{"type": "contains", "value": "invoice"},
                 {"type": "regex", "value": "^ERROR: .+"},
                 {"type": "not_contains", "value": "TODO"},
                 {"type": "json_path", "path": "result.count", "value": 3},
                 {"type": "llm-rubric", "value": "names the failing step"}]}

outputs.jsonl, one object per sample::

    {"id": "c1", "sample": 0, "output": "..."}

Deterministic assert types are graded here. ``llm-rubric`` asserts need a judge
verdict supplied with --rubrics, otherwise they are reported UNJUDGED and do not
silently count as passes.

Exit codes: 0 every case passed at the required threshold, 1 a case failed or an
assert went unjudged, 2 usage or unreadable input.
"""

import argparse
import json
import re
import sys

DETERMINISTIC = {"contains", "not_contains", "regex", "not_regex", "equals", "json_path"}


def load_jsonl(path, label):
    records = []
    try:
        with open(path, "r", encoding="utf-8") as handle:
            for lineno, line in enumerate(handle, start=1):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                try:
                    records.append(json.loads(line))
                except ValueError as exc:
                    raise ValueError("%s line %d is not JSON: %s" % (label, lineno, exc))
    except OSError as exc:
        raise ValueError("cannot read %s: %s" % (label, exc))
    return records


def dig(payload, path):
    """Resolve a dotted path with optional [index] segments."""
    current = payload
    for raw in path.split("."):
        if not raw:
            continue
        name = raw
        indexes = []
        while name.endswith("]") and "[" in name:
            head, _, tail = name.rpartition("[")
            indexes.insert(0, int(tail[:-1]))
            name = head
        if name:
            if not isinstance(current, dict) or name not in current:
                return None, False
            current = current[name]
        for index in indexes:
            if not isinstance(current, list) or index >= len(current):
                return None, False
            current = current[index]
    return current, True


def grade_assert(spec, output):
    """Return (state, detail) where state is pass, fail or unjudged."""
    kind = spec.get("type", "contains")
    value = spec.get("value")
    if kind == "contains":
        return ("pass" if str(value) in output else "fail", "substring %r" % value)
    if kind == "not_contains":
        return ("fail" if str(value) in output else "pass", "absent %r" % value)
    if kind == "equals":
        return ("pass" if output.strip() == str(value).strip() else "fail", "exact match")
    if kind in ("regex", "not_regex"):
        try:
            hit = re.search(str(value), output, re.MULTILINE | re.DOTALL) is not None
        except re.error as exc:
            return ("fail", "bad pattern: %s" % exc)
        wanted = kind == "regex"
        return ("pass" if hit == wanted else "fail", "pattern %r" % value)
    if kind == "json_path":
        try:
            payload = json.loads(output)
        except ValueError:
            return ("fail", "output is not JSON")
        path = spec.get("path", "")
        found, ok = dig(payload, path)
        if not ok:
            return ("fail", "path %s absent" % path)
        if "value" not in spec:
            return ("pass", "path %s present" % path)
        return (
            "pass" if found == value else "fail",
            "path %s is %r, wanted %r" % (path, found, value),
        )
    if kind == "llm-rubric":
        return ("unjudged", "rubric: %s" % value)
    return ("fail", "unknown assert type %r" % kind)


def apply_rubrics(case_id, sample, index, rubrics):
    key = (str(case_id), int(sample), int(index))
    return rubrics.get(key)


def grade(cases, outputs, rubrics, threshold_mode, k_default):
    by_case = {}
    for record in outputs:
        by_case.setdefault(str(record.get("id")), []).append(record)

    rows = []
    for case in cases:
        case_id = str(case.get("id"))
        samples = sorted(
            by_case.get(case_id, []), key=lambda r: int(r.get("sample", 0) or 0)
        )
        specs = case.get("asserts") or []
        sample_results = []
        for position, record in enumerate(samples):
            output = record.get("output")
            if not isinstance(output, str):
                output = json.dumps(output)
            sample_index = int(record.get("sample", position) or 0)
            details = []
            for index, spec in enumerate(specs):
                state, detail = grade_assert(spec, output)
                if state == "unjudged":
                    verdict = apply_rubrics(case_id, sample_index, index, rubrics)
                    if verdict is not None:
                        state = "pass" if verdict.get("pass") else "fail"
                        detail = verdict.get("reason", detail)
                details.append(
                    {"index": index, "type": spec.get("type"), "state": state, "detail": detail}
                )
            sample_results.append(
                {
                    "sample": sample_index,
                    "passed": all(d["state"] == "pass" for d in details) and bool(details),
                    "unjudged": any(d["state"] == "unjudged" for d in details),
                    "asserts": details,
                }
            )
        k = int(case.get("k", k_default) or k_default)
        passing = sum(1 for s in sample_results if s["passed"])
        unjudged = sum(1 for s in sample_results if s["unjudged"])
        mode = case.get("mode", threshold_mode)
        if not sample_results:
            verdict = "NO-OUTPUT"
        elif unjudged:
            verdict = "UNJUDGED"
        elif mode == "pass^k":
            verdict = "PASS" if passing == len(sample_results) else "FAIL"
        else:
            verdict = "PASS" if passing >= 1 else "FAIL"
        rows.append(
            {
                "id": case_id,
                "suite": case.get("suite", "capability"),
                "mode": mode,
                "k": k,
                "samples": len(sample_results),
                "passing": passing,
                "unjudged": unjudged,
                "verdict": verdict,
                "asserts": len(specs),
                "detail": sample_results,
            }
        )
    return rows


def render(rows):
    lines = [
        "%-18s %-11s %-7s %-8s %-8s %s" % ("CASE", "SUITE", "MODE", "SAMPLES", "PASSING", "VERDICT"),
        "-" * 68,
    ]
    for row in rows:
        lines.append(
            "%-18s %-11s %-7s %-8d %-8d %s"
            % (
                row["id"][:18],
                row["suite"][:11],
                row["mode"],
                row["samples"],
                row["passing"],
                row["verdict"],
            )
        )
    failed = [r for r in rows if r["verdict"] not in ("PASS",)]
    lines.append("-" * 68)
    lines.append("%d of %d cases passed" % (len(rows) - len(failed), len(rows)))
    for row in failed:
        for sample in row["detail"]:
            for item in sample["asserts"]:
                if item["state"] != "pass":
                    lines.append(
                        "  %s sample %d assert %d (%s) %s: %s"
                        % (
                            row["id"],
                            sample["sample"],
                            item["index"],
                            item["type"],
                            item["state"].upper(),
                            item["detail"],
                        )
                    )
    return "\n".join(lines)


def build_parser():
    parser = argparse.ArgumentParser(
        prog="eval_runner.py",
        description="Grade outputs JSONL against a cases JSONL of typed assertions.",
    )
    parser.add_argument("cases", help="path to cases.jsonl")
    parser.add_argument("outputs", help="path to outputs.jsonl")
    parser.add_argument(
        "--rubrics",
        default="",
        help="optional judgements JSONL: {id, sample, assert_index, pass, reason}",
    )
    parser.add_argument(
        "--mode",
        choices=["pass@k", "pass^k"],
        default="pass@k",
        help="default threshold when a case does not set its own (default pass@k)",
    )
    parser.add_argument("--k", type=int, default=1, help="default k when a case omits it")
    parser.add_argument(
        "--suite", default="", help="grade only cases whose suite matches this value"
    )
    parser.add_argument("--json", action="store_true", help="emit the full report as JSON")
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        cases = load_jsonl(args.cases, "cases")
        outputs = load_jsonl(args.outputs, "outputs")
        rubrics = {}
        if args.rubrics:
            for record in load_jsonl(args.rubrics, "rubrics"):
                key = (
                    str(record.get("id")),
                    int(record.get("sample", 0) or 0),
                    int(record.get("assert_index", 0) or 0),
                )
                rubrics[key] = record
    except ValueError as exc:
        payload = {"error": str(exc)}
        print(json.dumps(payload) if args.json else "error: %s" % exc)
        return 2
    if args.suite:
        cases = [c for c in cases if c.get("suite") == args.suite]
    if not cases:
        message = "no cases to grade"
        print(json.dumps({"error": message}) if args.json else "error: %s" % message)
        return 2
    rows = grade(cases, outputs, rubrics, args.mode, args.k)
    if args.json:
        print(json.dumps({"cases": rows}, indent=2))
    else:
        print(render(rows))
    return 1 if any(row["verdict"] != "PASS" for row in rows) else 0


if __name__ == "__main__":
    sys.exit(main())
