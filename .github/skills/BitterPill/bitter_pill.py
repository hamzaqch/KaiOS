#!/usr/bin/env python3
"""Measure an instruction file so an over-prompting audit has numbers.

Reports, per markdown section: line count, character count, and an
approximate token count (characters / 4). Flags numbered-step blocks longer
than eight items unless a keep-class comment sits within ten lines above the
block. Standard library only.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
NUMBERED = re.compile(r"^(\s*)(\d+)[.)]\s+\S")
KEEP = re.compile(r"<!--\s*keep:")
FENCE = re.compile(r"^\s*(```|~~~)")
STEP_LIMIT = 8
KEEP_LOOKBACK = 10


def approx_tokens(text: str) -> int:
    """Rough token estimate. Four characters per token is close enough to rank."""
    return math.ceil(len(text) / 4)


def mask_fences(lines: list[str]) -> list[bool]:
    """Return a per-line flag marking lines inside fenced code blocks."""
    inside = False
    flags = []
    for line in lines:
        if FENCE.match(line):
            flags.append(True)
            inside = not inside
            continue
        flags.append(inside)
    return flags


def find_step_blocks(lines: list[str]) -> list[dict]:
    """Find runs of numbered list items, longest-run semantics per block."""
    fenced = mask_fences(lines)
    blocks: list[dict] = []
    index = 0
    total = len(lines)
    while index < total:
        if fenced[index] or not NUMBERED.match(lines[index]):
            index += 1
            continue
        start = index
        count = 0
        cursor = index
        while cursor < total:
            line = lines[cursor]
            if not fenced[cursor] and NUMBERED.match(line):
                count += 1
                cursor += 1
                continue
            if line.strip() == "" or line.startswith(("  ", "\t")):
                # blank lines and indented continuations do not end a list
                lookahead = cursor + 1
                while lookahead < total and (
                    lines[lookahead].strip() == ""
                    or lines[lookahead].startswith(("  ", "\t"))
                ):
                    lookahead += 1
                if lookahead < total and not fenced[lookahead] and NUMBERED.match(lines[lookahead]):
                    cursor = lookahead
                    continue
            break
        window = lines[max(0, start - KEEP_LOOKBACK):start]
        blocks.append(
            {
                "start_line": start + 1,
                "items": count,
                "over_limit": count > STEP_LIMIT,
                "keep_tag": any(KEEP.search(w) for w in window),
            }
        )
        index = max(cursor, start + 1)
    return blocks


def split_sections(lines: list[str]) -> list[dict]:
    """Split on ATX headings. Text before the first heading becomes a preamble."""
    fenced = mask_fences(lines)
    sections: list[dict] = []
    current = {"heading": "(preamble)", "level": 0, "start_line": 1, "lines": []}
    for number, line in enumerate(lines):
        match = None if fenced[number] else HEADING.match(line)
        if match:
            if current["lines"] or current["heading"] != "(preamble)":
                sections.append(current)
            current = {
                "heading": match.group(2) or "(untitled)",
                "level": len(match.group(1)),
                "start_line": number + 1,
                "lines": [],
            }
            continue
        current["lines"].append(line)
    sections.append(current)
    return sections


def analyse(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    sections = []
    for section in split_sections(lines):
        body = "\n".join(section["lines"])
        sections.append(
            {
                "heading": section["heading"],
                "level": section["level"],
                "start_line": section["start_line"],
                "lines": len(section["lines"]),
                "chars": len(body),
                "approx_tokens": approx_tokens(body),
            }
        )
    blocks = find_step_blocks(lines)
    flagged = [b for b in blocks if b["over_limit"] and not b["keep_tag"]]
    return {
        "path": str(path),
        "total_lines": len(lines),
        "total_chars": len(text),
        "approx_tokens": approx_tokens(text),
        "sections": sections,
        "step_blocks": blocks,
        "flagged_step_blocks": flagged,
        "verdict": "flagged" if flagged else "clean",
    }


def render(report: dict) -> str:
    out = [
        "file: {0}".format(report["path"]),
        "total: {0} lines, {1} chars, ~{2} tokens".format(
            report["total_lines"], report["total_chars"], report["approx_tokens"]
        ),
        "",
        "{0:<44} {1:>6} {2:>8} {3:>8}".format("section", "lines", "chars", "~tokens"),
        "-" * 70,
    ]
    for section in sorted(report["sections"], key=lambda s: -s["approx_tokens"]):
        label = "{0}{1}".format("  " * max(0, section["level"] - 1), section["heading"])
        out.append(
            "{0:<44} {1:>6} {2:>8} {3:>8}".format(
                label[:44], section["lines"], section["chars"], section["approx_tokens"]
            )
        )
    out.append("")
    if report["flagged_step_blocks"]:
        out.append("numbered-step blocks over {0} items and untagged:".format(STEP_LIMIT))
        for block in report["flagged_step_blocks"]:
            out.append(
                "  line {0}: {1} items".format(block["start_line"], block["items"])
            )
    else:
        out.append("no untagged numbered-step blocks over {0} items".format(STEP_LIMIT))
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="bitter_pill.py",
        description="Measure a markdown instruction file for an over-prompting audit.",
    )
    parser.add_argument("path", nargs="?", help="markdown file to measure")
    parser.add_argument("--json", action="store_true", help="emit the report as JSON")
    args = parser.parse_args(argv)

    if not args.path:
        parser.print_usage()
        print("error: a markdown file path is required", file=sys.stderr)
        return 2
    target = Path(args.path)
    if not target.is_file():
        print("error: not a file: {0}".format(target), file=sys.stderr)
        return 1
    report = analyse(target)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(render(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
