---
name: markdown-docs
description: Rules for every Markdown file — freshness frontmatter, plain prose, short paragraphs, one home per fact, no walls of text.
applyTo: "**/*.md"
version: 1.0.0
last_updated: 2026-09-28T00:00:00Z
convention: kaios-freshness-v1
---

# Markdown

## Freshness frontmatter

Every document carries it:

```yaml
---
version: 1.0.0
last_updated: 2026-09-28T00:00:00Z
convention: kaios-freshness-v1
---
```

`version` moves when the content changes meaningfully, not on a typo fix. `last_updated` is ISO 8601 with a `Z`. Auto-generated documents also name their source and generator so nobody edits the output by hand.

Skill and agent files carry their own required frontmatter instead; this rule covers everything else.

## One home per fact

A fact stated in two documents will disagree with itself within a month, and the reader has no way to tell which copy is current. So each fact has exactly one home and everything else links to it.

When writing something that already exists elsewhere, link instead. When two places genuinely both need it, pick the home, cut the other to a pointer, and say where it went.

## Plain prose

- One idea per sentence. About twenty words. Verbs, not nouns pretending to be verbs.
- Paragraphs of two or three sentences with whitespace between them. If a paragraph runs past four lines, break it or make it a list.
- Plain words. "Use", not "leverage". "Before", not "prior to". If a word would look out of place in a plainly written essay, cut it.
- No marketing register. No "powerful", "seamless", "robust", "comprehensive", "cutting-edge". A document describing infrastructure does not need to sell it.
- Say what a thing does before saying why it is good. Most of the time the second half is unnecessary.
- Write "verified" or "not verified". Never "should work".

## Structure

- Tables for anything side by side: options, mappings, comparisons, inventories. A table is scannable in a way that four parallel paragraphs are not.
- Bullets for list-shaped content, at most two levels of nesting. If a third level is needed, restructure.
- Bold the first few words of a bullet when it has a label, never the whole sentence.
- Headings that say what the section contains, not what category it belongs to.
- A code block for anything that gets copied: a command, a file shape, a payload. Never a command inline in a sentence when the reader is meant to run it.
- No decorative emoji in headings or prose. The response format's markers are a contract and are exempt.

## What a document opens with

The thing the reader came for. A blockquote under the title saying in one or two sentences what this file is and when to load it, then straight into content.

No section restating the title. No preamble explaining that documentation is important. No closing summary repeating what the document just said.

## Links

Relative paths within the repository, and every one resolves — `python -m kaios integrity docs` fails on a link that does not. Link to the file, not to a heading inside it, unless the heading is the point.

Refer to a file by its path when the reader has to go there, and describe it in words otherwise. A path in every sentence makes prose unreadable.

## What not to write

- A changelog section inside a design document. Git is the changelog; `git log -- <path>` is the record.
- A history of how the document used to read. If the old version matters, it is in git.
- An empty section as a placeholder. A section appears when it has content.
- A rule that a capable reader makes unnecessary. Ask whether a smarter reader would need the line, and cut it if not.
- Anything personal: a name, a home directory path, a private hostname, a credential, an internal identifier that does not belong in a repository meant to be shared with a team.
