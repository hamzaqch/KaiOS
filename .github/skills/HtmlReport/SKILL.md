---
name: html-report
description: Turn an analysis that already exists into one self-contained HTML file that can be attached to a ticket, mailed, or opened offline. The model writes a JSON spec of title, sections, markdown bodies, and tables; a bundled renderer owns all layout, typography, and colour, including a light and a dark palette and no external assets. USE WHEN html report, render as HTML, make this a page, single file report, shareable report, export this analysis, printable version, attach this to the ticket, standalone html, offline report. NOT FOR building a web application or a site (write the project code), producing the analysis itself (run the analysis skill first), or any output that needs to stay a markdown file in the repository.
argument-hint: "<what to render> [--out path.html]"
---

# HTML Report

Rendering is a tool's job. The model decides what the report says; the renderer decides how it looks.

## USE WHEN / NOT FOR

USE WHEN an analysis already exists and someone outside this session needs to open, print, or attach it.

NOT FOR building a site or an application, or producing the analysis itself, which belongs to whichever skill does that work first.

## What this produces

One HTML file that opens correctly with no network.

## Done looks like

- The analysis existed before this skill ran. This skill formats; it does not invent content to fill sections.
- Every section in the source analysis appears, with its tables as real tables rather than as preformatted text.
- The file references nothing external. No fonts, no scripts, no images by URL.
- It is readable in both light and dark appearance, because the renderer ships both palettes.
- Wide tables scroll inside their own container instead of making the page scroll sideways.
- The written path is reported, along with the byte size and section count from the tool.

## Spec shape

<!-- keep: output-schema -->
```json
{
  "title": "string, required",
  "subtitle": "string, optional",
  "meta": {"label": "value"},
  "sections": [
    {
      "heading": "string",
      "body_md": "markdown — paragraphs, ## headings, lists, > quotes, `code`, fenced blocks, links, pipe tables",
      "table": {"columns": ["..."], "rows": [["..."]]}
    }
  ],
  "footer": "string, optional"
}
```

A section may carry `body_md`, `table`, or both. `meta` renders as a row of chips under the title and is the right place for depth, date, verdict, and scope. Any cell whose text is exactly critical, high, medium, or low is coloured by severity, which is why findings tables should use those four words verbatim.

## Tool contract

<!-- keep: tool-contract -->
```
python .github/skills/HtmlReport/render_report.py --spec spec.json --out report.html
python .github/skills/HtmlReport/render_report.py --stdin --out report.html --json
python .github/skills/HtmlReport/render_report.py --spec spec.json --print
python .github/skills/HtmlReport/render_report.py --help
```

`--stdin` reads the spec from standard input, `--print` writes the document to standard output instead of a file, and `--json` prints the result as `{"ok", "out", "bytes", "sections"}`. Default output path is `report.html` in the working directory. Exit codes are 0 for a render, 1 for an unreadable or non-object spec, 2 for missing arguments. The renderer uses the standard library only and never reaches the network.

## Roles

Write the spec at the **high** role; deciding what belongs in the report is the only judgment left once the analysis exists, and it is modest. Do not spend a **max** role run on formatting.

## Constraints and gotchas

- Write the spec to a file rather than passing a long JSON string on a command line. Windows command lines truncate, and quoting rules differ between shells.
- Keep markdown inside `body_md` simple. The renderer supports the common constructs listed in the spec and ignores the exotic ones; deeply nested lists and inline HTML are not supported.
- Do not put styling in the content. There is no way to override the palette from a spec, and that is deliberate.
- Escape nothing by hand. The renderer escapes everything, so double-escaped content will show its own entities.
- Do not render sensitive material into a file destined for an attachment without saying so. The file is trivially forwardable once it exists.
- Regenerate rather than hand-edit the HTML. An edited output file is lost on the next render.
