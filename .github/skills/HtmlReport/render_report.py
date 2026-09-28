#!/usr/bin/env python3
"""Render a JSON report spec into one self-contained HTML file.

No external assets, no network, no third-party packages. CSS is inlined and
carries both a light and a dark palette selected by prefers-color-scheme.
The spec shape is documented in SKILL.md; a minimal spec is
{"title": "...", "sections": [{"heading": "...", "body_md": "..."}]}.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path

CSS = """
:root {
  color-scheme: light dark;
  --bg: #fbfaf8; --panel: #ffffff; --ink: #1b1b1f; --muted: #5d6068;
  --line: #e3e1dc; --accent: #2f5d8c; --chip: #f1efea; --code: #f5f3ef;
  --crit: #a3282a; --high: #b3671c; --med: #7a6a1f; --low: #4b5563;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #14161a; --panel: #1b1e23; --ink: #e9e8e4; --muted: #a2a6ae;
    --line: #2c3037; --accent: #86b2dc; --chip: #23272e; --code: #1f2329;
    --crit: #f08a84; --high: #e0ac6a; --med: #cfc07a; --low: #aab2bd;
  }
}
* { box-sizing: border-box; }
body {
  margin: 0; background: var(--bg); color: var(--ink);
  font: 16px/1.62 -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
}
.wrap { max-width: 860px; margin: 0 auto; padding: 48px 20px 72px; }
header { border-bottom: 1px solid var(--line); padding-bottom: 20px; margin-bottom: 8px; }
h1 { font-size: 1.85rem; line-height: 1.24; margin: 0 0 6px; letter-spacing: -0.01em; }
.subtitle { color: var(--muted); margin: 0; font-size: 1.02rem; }
.meta { display: flex; flex-wrap: wrap; gap: 8px; margin: 16px 0 0; padding: 0; list-style: none; }
.meta li {
  background: var(--chip); border: 1px solid var(--line); border-radius: 999px;
  padding: 3px 11px; font-size: 0.79rem; color: var(--muted);
}
.meta b { color: var(--ink); font-weight: 600; }
section { margin-top: 38px; }
h2 { font-size: 1.22rem; margin: 0 0 12px; padding-bottom: 6px; border-bottom: 1px solid var(--line); }
h3 { font-size: 1.04rem; margin: 22px 0 8px; }
h4 { font-size: 0.95rem; margin: 18px 0 6px; color: var(--muted); }
p { margin: 0 0 12px; }
ul, ol { margin: 0 0 12px; padding-left: 24px; }
li { margin: 4px 0; }
blockquote {
  margin: 0 0 14px; padding: 8px 16px; border-left: 3px solid var(--accent);
  background: var(--panel); color: var(--muted);
}
a { color: var(--accent); }
code {
  background: var(--code); border: 1px solid var(--line); border-radius: 4px;
  padding: 1px 5px; font-family: ui-monospace, "Cascadia Mono", Consolas, monospace;
  font-size: 0.88em;
}
pre {
  background: var(--code); border: 1px solid var(--line); border-radius: 8px;
  padding: 14px 16px; overflow-x: auto; margin: 0 0 14px;
}
pre code { background: none; border: 0; padding: 0; font-size: 0.85rem; }
.tablewrap { overflow-x: auto; margin: 0 0 14px; border: 1px solid var(--line); border-radius: 8px; }
table { border-collapse: collapse; width: 100%; font-size: 0.92rem; background: var(--panel); }
th, td { text-align: left; padding: 9px 12px; border-bottom: 1px solid var(--line); vertical-align: top; }
th { font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--muted); }
tbody tr:last-child td { border-bottom: 0; }
td.critical { color: var(--crit); font-weight: 600; }
td.high { color: var(--high); font-weight: 600; }
td.medium { color: var(--med); }
td.low { color: var(--low); }
footer {
  margin-top: 48px; padding-top: 16px; border-top: 1px solid var(--line);
  color: var(--muted); font-size: 0.84rem;
}
img { max-width: 100%; }
@media print { body { background: #fff; } .wrap { padding: 0; } }
"""

SEVERITIES = {"critical", "high", "medium", "low"}
CODE_SPAN = re.compile(r"`([^`]+)`")
LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
BOLD = re.compile(r"\*\*([^*]+)\*\*")
ITALIC = re.compile(r"(?<![*\w])\*([^*\n]+)\*(?!\*)")
HEADING = re.compile(r"^(#{2,6})\s+(.*)$")
BULLET = re.compile(r"^\s*[-*+]\s+(.*)$")
ORDERED = re.compile(r"^\s*\d+[.)]\s+(.*)$")
FENCE = re.compile(r"^\s*(?:```|~~~)\s*(\w*)\s*$")
QUOTE = re.compile(r"^>\s?(.*)$")
ROW = re.compile(r"^\s*\|(.+)\|\s*$")
DIVIDER = re.compile(r"^[\s|:-]+$")


def inline(text: str) -> str:
    """Escape, then apply inline markdown. Code spans are protected first."""
    spans: list[str] = []

    def stash(match: re.Match) -> str:
        spans.append(html.escape(match.group(1), quote=False))
        return "\x00{0}\x00".format(len(spans) - 1)

    text = CODE_SPAN.sub(stash, text)
    text = html.escape(text, quote=False)
    text = LINK.sub(
        lambda m: '<a href="{0}">{1}</a>'.format(html.escape(m.group(2), quote=True), m.group(1)),
        text,
    )
    text = BOLD.sub(lambda m: "<strong>{0}</strong>".format(m.group(1)), text)
    text = ITALIC.sub(lambda m: "<em>{0}</em>".format(m.group(1)), text)
    for index, span in enumerate(spans):
        text = text.replace("\x00{0}\x00".format(index), "<code>{0}</code>".format(span))
    return text


def split_row(line: str) -> list[str]:
    inner = ROW.match(line).group(1)
    return [cell.strip() for cell in inner.split("|")]


def cell_class(value: str) -> str:
    key = value.strip().lower()
    return ' class="{0}"'.format(key) if key in SEVERITIES else ""


def render_table(columns: list, rows: list) -> str:
    head = "".join("<th>{0}</th>".format(inline(str(c))) for c in columns)
    body = []
    for row in rows:
        cells = []
        for value in row:
            text = "" if value is None else str(value)
            cells.append("<td{0}>{1}</td>".format(cell_class(text), inline(text)))
        body.append("<tr>{0}</tr>".format("".join(cells)))
    return (
        '<div class="tablewrap"><table><thead><tr>{0}</tr></thead>'
        "<tbody>{1}</tbody></table></div>"
    ).format(head, "".join(body))


def render_markdown(source: str) -> str:
    lines = (source or "").replace("\r\n", "\n").split("\n")
    out: list[str] = []
    buffer: list[str] = []
    index = 0

    def flush_paragraph() -> None:
        if buffer:
            out.append("<p>{0}</p>".format(inline(" ".join(buffer).strip())))
            buffer.clear()

    while index < len(lines):
        line = lines[index]
        fence = FENCE.match(line)
        if fence:
            flush_paragraph()
            index += 1
            block: list[str] = []
            while index < len(lines) and not FENCE.match(lines[index]):
                block.append(lines[index])
                index += 1
            index += 1
            out.append(
                "<pre><code>{0}</code></pre>".format(
                    html.escape("\n".join(block), quote=False)
                )
            )
            continue
        if not line.strip():
            flush_paragraph()
            index += 1
            continue
        heading = HEADING.match(line)
        if heading:
            flush_paragraph()
            level = min(6, len(heading.group(1)) + 1)
            out.append("<h{0}>{1}</h{0}>".format(level, inline(heading.group(2))))
            index += 1
            continue
        if ROW.match(line):
            flush_paragraph()
            block = []
            while index < len(lines) and ROW.match(lines[index]):
                block.append(lines[index])
                index += 1
            cleaned = [b for b in block if not DIVIDER.match(b.strip().strip("|"))]
            if cleaned:
                columns = split_row(cleaned[0])
                rows = [split_row(b) for b in cleaned[1:]]
                out.append(render_table(columns, rows))
            continue
        if QUOTE.match(line):
            flush_paragraph()
            block = []
            while index < len(lines) and QUOTE.match(lines[index]):
                block.append(QUOTE.match(lines[index]).group(1))
                index += 1
            out.append("<blockquote>{0}</blockquote>".format(inline(" ".join(block))))
            continue
        for pattern, tag in ((BULLET, "ul"), (ORDERED, "ol")):
            if pattern.match(line):
                flush_paragraph()
                items = []
                while index < len(lines) and pattern.match(lines[index]):
                    items.append(pattern.match(lines[index]).group(1))
                    index += 1
                out.append(
                    "<{0}>{1}</{0}>".format(
                        tag, "".join("<li>{0}</li>".format(inline(i)) for i in items)
                    )
                )
                break
        else:
            buffer.append(line.strip())
            index += 1
    flush_paragraph()
    return "\n".join(out)


def render(spec: dict) -> str:
    title = str(spec.get("title") or "Report")
    subtitle = spec.get("subtitle")
    meta = spec.get("meta") or {}
    sections = spec.get("sections") or []
    footer = spec.get("footer")

    head = ['<h1>{0}</h1>'.format(inline(title))]
    if subtitle:
        head.append('<p class="subtitle">{0}</p>'.format(inline(str(subtitle))))
    if isinstance(meta, dict) and meta:
        chips = "".join(
            "<li><b>{0}</b> {1}</li>".format(inline(str(k)), inline(str(v)))
            for k, v in meta.items()
        )
        head.append('<ul class="meta">{0}</ul>'.format(chips))

    body = []
    for section in sections:
        if not isinstance(section, dict):
            continue
        parts = []
        heading = section.get("heading")
        if heading:
            parts.append("<h2>{0}</h2>".format(inline(str(heading))))
        if section.get("body_md"):
            parts.append(render_markdown(str(section["body_md"])))
        table = section.get("table")
        if isinstance(table, dict) and table.get("columns"):
            parts.append(render_table(table["columns"], table.get("rows") or []))
        body.append("<section>{0}</section>".format("\n".join(parts)))

    tail = "<footer>{0}</footer>".format(inline(str(footer))) if footer else ""
    return (
        "<!doctype html>\n"
        '<html lang="en"><head><meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "<title>{title}</title>\n<style>{css}</style>\n</head>\n<body>\n"
        '<div class="wrap">\n<header>{head}</header>\n{body}\n{tail}\n</div>\n'
        "</body></html>\n"
    ).format(
        title=html.escape(title, quote=False),
        css=CSS,
        head="\n".join(head),
        body="\n".join(body),
        tail=tail,
    )


def load_spec(args: argparse.Namespace) -> dict:
    if args.stdin:
        return json.loads(sys.stdin.read())
    return json.loads(Path(args.spec).read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="render_report.py",
        description="Render a JSON report spec into one self-contained HTML file.",
    )
    parser.add_argument("--spec", help="path to the JSON spec file")
    parser.add_argument("--stdin", action="store_true", help="read the spec from stdin")
    parser.add_argument("--out", help="output HTML path (default report.html)")
    parser.add_argument("--json", action="store_true", help="print the result as JSON")
    parser.add_argument("--print", action="store_true", help="write the HTML to stdout")
    args = parser.parse_args(argv)

    if not args.spec and not args.stdin:
        parser.print_usage()
        print("error: pass --spec <file> or --stdin", file=sys.stderr)
        return 2
    try:
        spec = load_spec(args)
    except (OSError, ValueError) as error:
        print("error: could not read spec — {0}".format(error), file=sys.stderr)
        return 1
    if not isinstance(spec, dict):
        print("error: spec must be a JSON object", file=sys.stderr)
        return 1

    document = render(spec)
    if args.print:
        sys.stdout.write(document)
        return 0
    target = Path(args.out or "report.html")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(document, encoding="utf-8")
    result = {
        "ok": True,
        "out": str(target),
        "bytes": len(document.encode("utf-8")),
        "sections": len(spec.get("sections") or []),
    }
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("wrote {0} ({1} bytes, {2} sections)".format(result["out"], result["bytes"], result["sections"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
