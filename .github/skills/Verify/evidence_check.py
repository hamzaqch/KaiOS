#!/usr/bin/env python3
"""Report closed ISA claims that carry no evidence stub.

A claim marked ``- [x] ISC-N: ...`` must end with ``- evidence: <stub>`` naming
the probe that closed it. This tool parses an ISA and lists every closed claim
that does not, so the gap is visible before anyone trusts the checkbox.

Exit codes: 0 every closed claim has a stub, 1 at least one does not,
2 usage or unreadable input.
"""

import argparse
import json
import re
import sys

# "- [x] ISC-12: text"  /  "* [X] ISC-12 - text"
CLAIM = re.compile(
    r"^\s*[-*]\s*\[(?P<mark>[ xX])\]\s*(?P<cid>ISC-\d+)\s*[:.\-]?\s*(?P<body>.*)$"
)
# em dash, en dash or hyphen, then "evidence:"
EVIDENCE = re.compile(r"[—–-]\s*evidence\s*:\s*(?P<stub>.+?)\s*$", re.IGNORECASE)
DROPPED = re.compile(r"\[DROPPED\s*:", re.IGNORECASE)
FALSIFIER = re.compile(r"\bfalsifier\s*:", re.IGNORECASE)


def parse_claims(text):
    """Return a list of claim dicts in file order."""
    claims = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        match = CLAIM.match(line)
        if not match:
            continue
        body = match.group("body")
        stub_match = EVIDENCE.search(body)
        stub = stub_match.group("stub").strip() if stub_match else ""
        claims.append(
            {
                "id": match.group("cid"),
                "line": lineno,
                "closed": match.group("mark").lower() == "x",
                "dropped": bool(DROPPED.search(body)),
                "has_falsifier": bool(FALSIFIER.search(body)),
                "evidence": stub,
                "text": body.strip(),
            }
        )
    return claims


def audit(claims, check_falsifiers=False):
    """Split claims into the report buckets."""
    closed = [c for c in claims if c["closed"] and not c["dropped"]]
    missing = [c for c in closed if not c["evidence"]]
    weak = [c for c in closed if c["evidence"] and len(c["evidence"]) < 4]
    open_claims = [c for c in claims if not c["closed"] and not c["dropped"]]
    report = {
        "claims_total": len(claims),
        "closed": len(closed),
        "open": len(open_claims),
        "dropped": sum(1 for c in claims if c["dropped"]),
        "missing_evidence": [
            {"id": c["id"], "line": c["line"], "text": c["text"][:120]} for c in missing
        ],
        "weak_evidence": [
            {"id": c["id"], "line": c["line"], "evidence": c["evidence"]} for c in weak
        ],
    }
    if check_falsifiers:
        report["missing_falsifier"] = [
            {"id": c["id"], "line": c["line"], "text": c["text"][:120]}
            for c in open_claims + closed
            if not c["has_falsifier"]
        ]
    return report


def render(report, path):
    lines = [
        "evidence check: %s" % path,
        "  claims %d   closed %d   open %d   dropped %d"
        % (
            report["claims_total"],
            report["closed"],
            report["open"],
            report["dropped"],
        ),
    ]
    if report["missing_evidence"]:
        lines.append("")
        lines.append("CLOSED WITHOUT EVIDENCE (%d):" % len(report["missing_evidence"]))
        for item in report["missing_evidence"]:
            lines.append("  line %-5d %-9s %s" % (item["line"], item["id"], item["text"]))
    if report["weak_evidence"]:
        lines.append("")
        lines.append("STUB TOO SHORT TO BE A PROBE (%d):" % len(report["weak_evidence"]))
        for item in report["weak_evidence"]:
            lines.append(
                "  line %-5d %-9s evidence: %s"
                % (item["line"], item["id"], item["evidence"])
            )
    if "missing_falsifier" in report and report["missing_falsifier"]:
        lines.append("")
        lines.append("NO FALSIFIER (%d):" % len(report["missing_falsifier"]))
        for item in report["missing_falsifier"]:
            lines.append("  line %-5d %-9s %s" % (item["line"], item["id"], item["text"]))
    if not report["missing_evidence"] and not report["weak_evidence"]:
        lines.append("")
        lines.append("OK: every closed claim names its evidence.")
    return "\n".join(lines)


def build_parser():
    parser = argparse.ArgumentParser(
        prog="evidence_check.py",
        description="List ISA claims marked closed that carry no evidence stub.",
    )
    parser.add_argument("isa", help="path to an ISA markdown file")
    parser.add_argument("--json", action="store_true", help="emit the report as JSON")
    parser.add_argument(
        "--falsifiers",
        action="store_true",
        help="also list claims with no Falsifier clause",
    )
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        with open(args.isa, "r", encoding="utf-8") as handle:
            text = handle.read()
    except OSError as exc:
        message = {"error": "cannot read ISA", "path": args.isa, "detail": str(exc)}
        print(json.dumps(message) if args.json else "error: %s" % message["detail"])
        return 2
    report = audit(parse_claims(text), check_falsifiers=args.falsifiers)
    report["path"] = args.isa
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(render(report, args.isa))
    problems = len(report["missing_evidence"]) + len(report["weak_evidence"])
    if args.falsifiers:
        problems += len(report.get("missing_falsifier", []))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
