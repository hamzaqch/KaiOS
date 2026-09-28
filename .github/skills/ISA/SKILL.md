---
name: isa
description: "Owns the Ideal State Artifact, the file that holds what done means for a project or a task. Scaffolds an ISA, interviews a half-formed idea into falsifiable claims, scores completeness, seeds an ISA from an existing repository, and appends decisions, log entries and remaining work. USE WHEN ISA, ISC, ideal state, what does done mean, write done down first, articulate done, project specification, spec this out, hill-climb, frontier, next claim, falsifier, anti-claim, grill me, discovery interview, half-formed idea, seed an ISA from this repo, ISA check, completeness score, remaining work. NOT FOR creating or editing skills (use create-skill), executing the work against an ISA (use algorithm), or closing a claim on evidence (use verify)."
argument-hint: "[scaffold|interview|check|seed|append] [slug or path]"
---

# ISA — the Ideal State Artifact

## What this produces

One Markdown file that states the ideal state of a project or a task as claims a probe can falsify. Every other part of KaiOS reads it: the Algorithm climbs its claims, the hooks gate on its evidence stubs, memory indexes it, and a resumed session recovers from it instead of from chat scrollback.

Two homes, and the choice is not cosmetic:

- **Project ISA** at `<repo>/ISA.md` — the repository's own ideal state. It outlives every task and every session.
- **Task ISA** at `$KAIOS_HOME/MEMORY/WORK/<slug>/ISA.md` — one unit of work that ends.

## Done looks like

- The file exists at the right home and `python -m kaios isa check <path>` exits 0.
- Every claim carries a falsifier naming the probe, not a feeling.
- At least one anti-claim states what must not happen.
- Everything still unknown sits under `Not yet specified` rather than being invented.
- `python -m kaios isa frontier <path>` returns at least one takeable claim, or the ISA is complete.
- The stated goal in frontmatter is the engineer's own words, unedited.

## USE WHEN

The work is worth more than one command, the goal is vague, a build is about to start, a session is resuming, or someone asks what done means here.

## NOT FOR

Skill authoring (`create-skill`). Running the work (`algorithm`). Closing claims on evidence (`verify`). A one-line answer needs no ISA.

## The artifact

Section order is fixed. A reader should be able to skim any two ISAs and find the same thing in the same place. Omit a section only when it would be empty, and never reorder.

| # | Section | Holds |
|---|---|---|
| 1 | `## Problem` | the current state, concretely, with its cost |
| 2 | `## Vision` | the ideal state as someone would experience it |
| 3 | `## Out of Scope` | what this deliberately will not do |
| 4 | `## Language` | terms with one meaning here, so claims stay readable |
| 5 | `## Principles` | the calls that were already made and stay made |
| 6 | `## Constraints` | hard limits: platform, runtime, policy, budget |
| 7 | `## Dependencies` | what must exist elsewhere first, and its state |
| 8 | `## Goal` | one paragraph naming the shippable outcome |
| 9 | `## Features` or `## Claims` | the claims themselves, grouped when there are many |
| 10 | `## Not yet specified` | the fog: known unknowns, named not guessed |
| 11 | `## Anti-claims` | what must not happen, each with its probe |
| 12 | `## Test Strategy` | claim id to probe to probe type |
| 13 | `## Decisions` | decisions with their reason, dead ends included |
| 14 | `## Log` | dated entries, newest last |
| 15 | `## Remaining Work` | what a reader should pick up next |

Use `## Features` with `### F1 · Name` subheads when the work has more than about a dozen claims; use a flat `## Claims` when it does not.

## Claim syntax

```
- [ ] ISC-7: The export writes one row per invoice line. Falsifier: a fixture with 3 lines produces 1 row.
- [ ] ISC-8: The export runs under 30s on the 50k fixture. Falsifier: timed run exceeds 30s. (after: ISC-7)
- [x] ISC-3: The CLI exits 2 on bad usage. Falsifier: any bad-usage path exits 0 or 1. — evidence: tests/test_cli.py::test_usage_exit
- [ ] ISC-5: [DROPPED: superseded by ISC-11] The export emitted CSV directly.
```

Rules that hold without exception:

- Ids are `ISC-N`, allocated once, never reused, never renumbered. A dropped claim keeps its id forever so that a decision written last month still resolves.
- `Falsifier:` names something runnable or readable. "Falsifier: it does not work" is not a falsifier.
- `(after: ISC-3)` declares an ordering edge, comma-separated for several. Edges are the only ordering signal; a claim's position in the list means nothing.
- A claim flips to `[x]` only with `— evidence: <stub>` appended: a test name, a commit hash, a command, a file path. One line, not a paragraph. The proof lives in the repository and in CI; the ISA points at it.
- A claim that is no longer wanted is tombstoned in place with `[DROPPED: reason]`, never deleted.

## Tool contracts

<!-- keep: tool-contract -->

| Command | Contract |
|---|---|
| `python -m kaios isa scaffold --slug S --goal G [--project]` | writes a new ISA from the template. `--project` targets `<repo>/ISA.md`, otherwise the task home. Prints the path as JSON. Refuses to overwrite. |
| `python -m kaios isa check <path>` | completeness and syntax. Exits non-zero when a claim lacks a falsifier, an id repeats, an `(after:)` names a missing id, a closed claim lacks an evidence stub, or a required section is missing. |
| `python -m kaios isa frontier <path>` | the claims takeable now: open, not dropped, every `(after:)` prerequisite closed. |
| `python -m kaios isa status <path>` | phase, progress, counts of open, closed, dropped. |
| `python -m kaios isa render <path> --md` | the ISA as a readable summary for pasting into a review. |
| `python -m kaios isa list` | every ISA the registry knows about. |

The scaffolder owns the frontmatter. Treat the fields it writes as canonical rather than hand-rolling them; at minimum it carries the slug, the task line, the phase, progress, the timestamps, and the stated goal verbatim.

## Scaffold

Ask nothing that the repository can answer. Read it first, then write a first draft of every section and show it. A draft with three thin sections and honest fog beats an interview that has not started.

The stated goal goes into frontmatter as the engineer wrote it, typos and all. It is the one string in the file that is never improved, because later drift is measured against it.

## Interview

For a half-formed idea, interrogate before scaffolding. The pattern is checkpointed, not a questionnaire:

- Ask at most three questions at a time, each one that would change what gets built. A question whose answer changes nothing is noise.
- After each batch, restate the shape you now believe in two or three sentences and let it be corrected. That restatement is the checkpoint.
- Push on the vague noun. "A dashboard", "a pipeline", "better errors" are placeholders; find out what the person would actually see.
- Ask for the failure that would make this a waste of time. That answer becomes an anti-claim.
- Ask what is explicitly out of scope, because engineers usually know this before they know the goal.
- Stop when a further question would not change a claim. Then scaffold, and drop everything still unresolved into `Not yet specified`.

Never invent an answer to keep the interview moving. Unanswered is a section, not a gap.

## Seed from a repository

When a codebase exists and its ideal state was never written down, derive the ISA from the code rather than from imagination.

- The README and any docs give Problem, Vision and Goal language. Quote, do not paraphrase into marketing.
- The test suite gives claims that are already true: each meaningful test is a claim closed with that test as its evidence stub.
- Entry points, CLI surface and public functions give claims that are asserted but unproven. Those open, with the missing probe as the falsifier.
- Config, lockfiles, CI workflows and platform files give Constraints and Dependencies.
- Anything the README promises that no test covers is the most valuable output of this workflow. It goes in as an open claim and usually surprises the owner.

## Append

The ISA at close is not the ISA at open. Fold new information in as it arrives, in the right section:

- A call that was made, with its reason, goes in `Decisions`. Dead ends belong there too; they are the cheapest thing in the file and the most reread.
- A dated one-liner goes in `Log` when something happened that a future reader needs: a probe failed, a constraint appeared, scope moved.
- What the next person should pick up goes in `Remaining Work`, replaced wholesale each time rather than accumulating.
- A discovery that splits a claim splits it: the original is tombstoned and two new ids appear.

Keep the changelog out. Version control is the change record; the ISA is the living design surface.

## Constraints and gotchas

- Never renumber to make the list look tidy. Stable ids are the whole point.
- Never soften a claim's wording to make it closeable. Split it or drop it with a reason.
- A container passing is not evidence for its members: "the suite is green" does not close a claim about one function.
- Progress in frontmatter is derived from the claims, not asserted. If they disagree, the claims are right.
- An ISA over roughly 600 lines has stopped being an ideal state and become a wiki. Split it by feature or promote a feature to its own project ISA.

A full worked example: [references/canonical-isa.md](references/canonical-isa.md).
