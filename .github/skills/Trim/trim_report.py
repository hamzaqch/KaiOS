#!/usr/bin/env python3
"""Find near-duplicate paragraphs and oversized sections in a markdown file.

Paragraphs are compared on normalised token sets (Jaccard overlap), so two
passages that say the same thing in different words still surface. Section sizes
show where the weight actually is, which is usually not where the author thinks.

The tool proposes nothing and edits nothing. It reports candidates; a human
approves every merge.

Exit codes: 0 nothing over threshold, 1 candidates found, 2 unreadable input.
"""

import argparse
import json
import re
import sys

WORD = re.compile(r"[a-z0-9][a-z0-9'_-]*")
HEADING = re.compile(r"^(#{1,6})\s+(?P<title>.+?)\s*#*$")
FENCE = re.compile(r"^\s*(```|~~~)")
DIRECTIVE = re.compile(
    r"\b(must|must not|never|always|do not|don't|required|forbidden|only when|shall)\b",
    re.IGNORECASE,
)
STOPWORDS = frozenset(
    """a an the and or but if then than that this these those of to in for on with by
    as at from is are was were be been being it its into over under about which who
    whom whose what when where how why not no nor so such can could may might will
    would should do does did done has have had having you your yours we our ours they
    their them he she his her i me my one two also more most less least very just only
    each every any some all both few other another same own too own s t""".split()
)


def normalise(text):
    tokens = WORD.findall(text.lower())
    return frozenset(t for t in tokens if t not in STOPWORDS and len(t) > 2)


def split_blocks(text):
    """Return paragraph blocks with line numbers, skipping fenced code."""
    blocks = []
    current = []
    start = 1
    in_fence = False
    section = ""
    for lineno, raw in enumerate(text.splitlines(), start=1):
        if FENCE.match(raw):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        heading = HEADING.match(raw)
        if heading:
            if current:
                blocks.append((start, "\n".join(current), section))
                current = []
            section = heading.group("title")
            continue
        if not raw.strip():
            if current:
                blocks.append((start, "\n".join(current), section))
                current = []
            continue
        if not current:
            start = lineno
        current.append(raw)
    if current:
        blocks.append((start, "\n".join(current), section))
    return blocks


def jaccard(left, right):
    if not left or not right:
        return 0.0
    union = len(left | right)
    if union == 0:
        return 0.0
    return len(left & right) / float(union)


def section_sizes(text):
    sizes = []
    current = {"title": "(preamble)", "line": 1, "chars": 0, "lines": 0}
    in_fence = False
    for lineno, raw in enumerate(text.splitlines(), start=1):
        if FENCE.match(raw):
            in_fence = not in_fence
        heading = HEADING.match(raw) if not in_fence else None
        if heading and len(heading.group(1)) <= 2:
            sizes.append(current)
            current = {
                "title": heading.group("title"),
                "line": lineno,
                "chars": 0,
                "lines": 0,
            }
            continue
        current["chars"] += len(raw) + 1
        current["lines"] += 1
    sizes.append(current)
    return [s for s in sizes if s["lines"] > 0]


def analyse(text, threshold, min_tokens):
    blocks = split_blocks(text)
    scored = [
        (start, body, section, normalise(body))
        for start, body, section in blocks
        if len(normalise(body)) >= min_tokens
    ]
    pairs = []
    for i in range(len(scored)):
        for j in range(i + 1, len(scored)):
            overlap = jaccard(scored[i][3], scored[j][3])
            if overlap >= threshold:
                pairs.append(
                    {
                        "similarity": round(overlap, 3),
                        "a": {
                            "line": scored[i][0],
                            "section": scored[i][2],
                            "excerpt": " ".join(scored[i][1].split())[:150],
                        },
                        "b": {
                            "line": scored[j][0],
                            "section": scored[j][2],
                            "excerpt": " ".join(scored[j][1].split())[:150],
                        },
                    }
                )
    pairs.sort(key=lambda p: -p["similarity"])
    sections = sorted(section_sizes(text), key=lambda s: -s["chars"])
    directives = sum(1 for line in text.splitlines() if DIRECTIVE.search(line))
    return {
        "chars": len(text),
        "lines": len(text.splitlines()),
        "paragraphs": len(blocks),
        "compared": len(scored),
        "directive_lines": directives,
        "duplicate_pairs": pairs,
        "sections_by_size": sections,
    }


def render(report, path, top):
    lines = [
        "trim report: %s" % path,
        "  %d chars   %d lines   %d paragraphs   %d directive lines"
        % (
            report["chars"],
            report["lines"],
            report["paragraphs"],
            report["directive_lines"],
        ),
        "",
        "HEAVIEST SECTIONS:",
    ]
    for section in report["sections_by_size"][:top]:
        lines.append(
            "  %6d chars  line %-5d %s"
            % (section["chars"], section["line"], section["title"])
        )
    lines.append("")
    if report["duplicate_pairs"]:
        lines.append("NEAR-DUPLICATE PARAGRAPHS (%d):" % len(report["duplicate_pairs"]))
        for pair in report["duplicate_pairs"][:top]:
            lines.append("")
            lines.append(
                "  similarity %.2f   line %d (%s)  vs  line %d (%s)"
                % (
                    pair["similarity"],
                    pair["a"]["line"],
                    pair["a"]["section"] or "-",
                    pair["b"]["line"],
                    pair["b"]["section"] or "-",
                )
            )
            lines.append("    A: %s" % pair["a"]["excerpt"])
            lines.append("    B: %s" % pair["b"]["excerpt"])
    else:
        lines.append("NEAR-DUPLICATE PARAGRAPHS: none above threshold.")
    lines.append("")
    lines.append("Nothing was changed. Every merge needs a human diff.")
    return "\n".join(lines)


def build_parser():
    parser = argparse.ArgumentParser(
        prog="trim_report.py",
        description="Report near-duplicate paragraphs and heavy sections in a markdown file.",
    )
    parser.add_argument("path", help="markdown file to analyse")
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.55,
        help="minimum token overlap to report a pair (default 0.55)",
    )
    parser.add_argument(
        "--min-tokens",
        type=int,
        default=8,
        help="ignore paragraphs with fewer meaningful tokens (default 8)",
    )
    parser.add_argument("--top", type=int, default=12, help="rows to print per table")
    parser.add_argument("--json", action="store_true", help="emit the report as JSON")
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        with open(args.path, "r", encoding="utf-8") as handle:
            text = handle.read()
    except OSError as exc:
        payload = {"error": "cannot read file", "path": args.path, "detail": str(exc)}
        print(json.dumps(payload) if args.json else "error: %s" % exc)
        return 2
    report = analyse(text, args.threshold, args.min_tokens)
    report["path"] = args.path
    report["threshold"] = args.threshold
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(render(report, args.path, args.top))
    return 1 if report["duplicate_pairs"] else 0


if __name__ == "__main__":
    sys.exit(main())
