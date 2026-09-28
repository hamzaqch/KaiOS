---
name: trim
description: "Shrinks a file that is loaded on every session and has grown past its budget, without losing a single directive. Finds near-duplicate passages, merges rules that say the same thing, relocates content that belongs in a path-scoped instructions file or a skill, and presents every change as a diff a human approves before it lands. USE WHEN trim, this file is too big, shrink the instructions, copilot-instructions is too long, reduce the context, prune a doctrine file, the rules are repetitive, duplicate rules, consolidate instructions, my always-on file is bloated, token budget, context budget, clean up the constitution, over the character limit. NOT FOR deleting rules you have decided are wrong (just delete them), refactoring code, cutting over-prompting from a whole system (use bitter-pill), or shortening prose for style."
argument-hint: "<path to the file to trim>"
---

# Trim — smaller file, same directives

## What this produces

A shorter version of an always-on file, plus a diff that accounts for every line removed. Each removal is one of three things and nothing else: a duplicate of a directive that survives elsewhere, a merge of two directives into one that says both, or a relocation to a file that loads only where the rule applies.

## Done looks like

- The file is under its stated budget, and the budget is written down somewhere.
- Every directive present before is present after, in exactly one place. The count is stated, not assumed.
- Each relocation names its new home, and that home actually loads where the rule applies.
- The diff was shown and approved before anything was written.
- `python .github/skills/Trim/trim_report.py <file>` shows no remaining near-duplicates above threshold.

## USE WHEN

An always-on file has grown past what it should cost: the top-level instructions, a path-scoped instructions file, an agent description, a skill body that has become a wiki.

## NOT FOR

Removing rules you have decided are wrong: that is a deletion, and it should be an explicit one. Code refactoring. Auditing a whole system for over-prompting (`bitter-pill` asks whether a rule should exist at all; this skill assumes every rule stays and finds a cheaper arrangement). Style editing.

## The one invariant

**No directive is lost.** Everything else is negotiable; this is not. A trim pass that quietly drops a rule is worse than an oversized file, because the rule's absence is invisible and its consequence arrives weeks later.

So the pass is bracketed by a count. Before: enumerate the directives, one line each, in a scratch list. After: walk the list and point at where each one now lives. A directive that cannot be pointed at was dropped, and the trim is not done.

A directive is any line that constrains behaviour: must, never, always, only when, do not, required, forbidden, or an imperative sentence that is clearly a rule. Examples and explanations are not directives, and they are where most of the weight sits.

## The three legal moves

**Dedupe.** The same rule stated twice, usually in different words, usually because two people added it a month apart. Keep the clearer statement, delete the other, and keep whichever location is more likely to be read. The report tool finds these by token overlap, which catches restatements that a string search misses.

**Merge.** Two directives that are one directive with two clauses. "Never commit secrets" and "store env var names only" merge into one rule that says both and is shorter than either pair. Merge only when the result is genuinely as strong: if the merged sentence is vaguer than the two it replaced, that is a loss disguised as a saving.

**Relocate.** The most valuable move and the most underused. A rule that only applies to one language, one directory, or one workflow does not belong in a file that loads everywhere.

| Content | Belongs in |
|---|---|
| a rule about one language or one directory | `.github/instructions/<topic>.instructions.md` with an `applyTo` glob |
| a rule about how to do one kind of task | the skill that owns that task |
| a worked example, a long table, a question bank | a `references/` file next to the skill |
| a narrative about something that broke | an incident note in memory, with the rule citing its id |
| a rule about one repository | that repository's own instructions file |

Relocation is not deletion, and it is not free: the new home must actually load when the rule matters. A rule moved into a glob that never matches is a dropped rule with extra steps. Check the glob against a real path before accepting the move.

## What to cut without mercy

Weight is rarely in the rules. It is in:

- Explanations of why a rule exists, restated at every rule. Keep the reason where it is genuinely non-obvious, cut it where the rule is self-evident.
- Examples of the obvious. One example earns its place when the shape is surprising. Three examples of the same shape are padding.
- Preambles, section introductions, and sentences that announce what the next section will say.
- Hedging and restatement. "It is important to note that" carries nothing.
- Rules written for a model that no longer needs them. This is `bitter-pill` territory, but when the pass surfaces one, flag it rather than silently keeping it.

## The human gate

<!-- keep: safety-gate -->

1. Report first. Run the tool, read the heaviest sections, and state the current size against the budget.
2. Enumerate the directives into a scratch list before touching the file. This list is the falsifier for the whole pass.
3. Propose the changes as a diff, grouped by move type, with the character saving per group.
4. Wait for approval. Do not write the file on the strength of "that looks right" about the plan; approval is of the diff.
5. Apply, then walk the directive list and point at each one's new location.
6. Report the before and after size, the directive count both times, and every relocation's new home.

This gate exists because a trim pass is the one operation that routinely looks successful while having destroyed something. The diff is cheap; the silent loss is not.

## Tool contracts

<!-- keep: tool-contract -->

| Command | Contract |
|---|---|
| `python .github/skills/Trim/trim_report.py <file.md>` | reports character and line counts, directive-line count, sections ranked by weight, and near-duplicate paragraph pairs by normalised token overlap. `--threshold F` tunes sensitivity (default 0.55), `--min-tokens N` ignores short paragraphs, `--top N` limits rows, `--json` for machine output. Exit 0 no pairs, 1 pairs found. Reads only; never writes. |

The overlap score is a hint. A pair at 0.8 is nearly always a true duplicate; a pair at 0.5 is worth reading and often is not. Two rules about the same subject that constrain different things will score high and must both survive.

## Constraints and gotchas

- Never trim a file you have not read end to end. Partial reading is how directives get dropped.
- Preserve the exact wording of anything that reads like a contract: a response format, a banned phrase list, an exit-code table. Paraphrasing a contract changes it.
- Do not reorder while trimming. Two changes at once makes the diff unreviewable, and the review is the safety property.
- Keep the file's frontmatter and version marker. Bump the version in the same change so the size drop is traceable.
- A file that needs trimming twice in a quarter has a structural problem: it is collecting rules that belong in path-scoped files. Fix the routing rather than trimming again.
