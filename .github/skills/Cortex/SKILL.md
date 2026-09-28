---
name: cortex
description: "The memory layer: capture what a run learned, search it back, read a digest of recent work, add and find durable knowledge notes, recall prior sessions and their ISAs from the work registry, and write an incident when something broke in a way worth never repeating. Decides which of those three homes a learning belongs in. USE WHEN remember this, what do we know about, did we do this before, prior work, recall, resume context, what did we learn, memory search, capture a note, knowledge base, add to knowledge, find a note, digest, weekly digest, memory health, write an incident, postmortem note, this broke before, cold start, catch me up. NOT FOR analysing why something failed in the first place (use root-cause-analysis), reading the current ISA (use isa), or searching the web (use research)."
argument-hint: "[capture|search|digest|knowledge|recall|incident] [query]"
---

# Cortex — what the system remembers

## What this produces

Three durable records, each with a different lifetime, plus the registry that makes prior work findable.

| Home | Lifetime | Holds |
|---|---|---|
| `$KAIOS_HOME/MEMORY/LEARNING/REFLECTIONS/*.jsonl` | weeks | captures: one line each, cheap, appended during a run |
| `$KAIOS_HOME/MEMORY/KNOWLEDGE/*.md` | indefinite | knowledge notes: a fact or rule that will be true next quarter |
| `$KAIOS_HOME/MEMORY/LEARNING/INCIDENTS/*.md` | indefinite | incidents: something broke, here is the narrative and the fix |
| `$KAIOS_HOME/MEMORY/STATE/work.json` | indefinite | the registry: every ISA, its slug, phase, progress and path |

## Done looks like

- `python -m kaios memory search <term>` finds the thing you just captured.
- A knowledge note has typed frontmatter and would still make sense to a teammate who was not there.
- An incident names what broke, the trigger, the blast radius, the fix, and the probe that would catch it next time.
- `python -m kaios memory health` reports no orphaned or unparsable records.
- A resumed session gets its context from here and from the ISA, never from chat history.

## USE WHEN

Something was learned, something needs finding again, a session is starting cold, or a teammate asks whether this has been hit before.

## NOT FOR

Diagnosing a failure (`root-cause-analysis` does the analysis; Cortex stores the result). Reading the active ISA (`isa`). Web search (`research`).

## Which home

This is the only decision in the skill that matters, and getting it wrong is how a memory system turns into a landfill.

- **Capture** when it is true about *this run*: a probe result, a surprising output, a path that was wrong, a preference the engineer stated in passing. Cheap, disposable, no formatting. Default to this. If you are unsure, capture.
- **Knowledge note** when it is true about *the world or the estate* and will still be true later: a system's actual behaviour as opposed to its documentation, a table's real grain, an API's undocumented limit, a convention the team settled on. A note that will be stale in a week is a capture, not a note.
- **Incident** when something *broke* and the sequence matters: what triggered it, what it took out, how long, what fixed it, and the probe that would have caught it. Incidents are narrative on purpose; a rule extracted from one belongs in an instructions file, citing the incident id.

Three things that are never memory: secrets of any kind, a copy of code that lives in version control, and a restatement of the ISA.

## Tool contracts

<!-- keep: tool-contract -->

| Command | Contract |
|---|---|
| `python -m kaios memory capture --kind K --text T` | appends one record to the hot layer. Kinds: `learning`, `gotcha`, `decision`, `preference`, `probe`, `incident-seed`. Prints the record id. |
| `python -m kaios memory search Q` | substring and token search across captures, knowledge and incidents. Returns matches with their home and date. |
| `python -m kaios memory digest [--since ISO]` | what recent runs learned, grouped by kind, for resume and for `upgrade`. |
| `python -m kaios memory health` | counts, date ranges, unparsable records, knowledge notes with no frontmatter. Non-zero when a record cannot be read. |
| `python -m kaios memory knowledge add` | writes a knowledge note with typed frontmatter. |
| `python -m kaios memory knowledge find Q` | searches knowledge notes only. |
| `python -m kaios isa list` | the work registry: every ISA with slug, phase and progress. |

Search before you write, every time. A second note on the same subject is worse than no note, because now two answers disagree and neither says which is current. When search finds an existing note, extend it and update its timestamp.

## Knowledge note shape

```markdown
---
type: system | dataset | convention | limit | contact-point
subject: invoice-tables
version: 1.0.0
last_updated: 2026-09-24T00:00:00Z
convention: kaios-freshness-v1
related: [nightly-export, finance-share]
---

# Invoice tables — real grain

One row per invoice **line**, not per invoice, despite the table name. A join on
invoice id fans out. Confirmed by counting distinct ids against row count on
2026-09-24: 41,208 rows over 12,455 invoices.
```

The frontmatter earns its place: `type` and `subject` are how retrieval narrows, `last_updated` is how a reader decides whether to trust it, and `related` is how one note leads to the next. A note without a date is a note nobody will rely on.

## Incident shape

Keep it to a page. Name the trigger, not a person.

```markdown
---
id: INC-20260923-parity-mask
version: 1.0.0
last_updated: 2026-09-23T00:00:00Z
convention: kaios-freshness-v1
severity: medium
---

# Approximate parity check masked a dropped join

**What broke.** The nightly export reported success for six days while silently
dropping about 4 percent of invoice lines.

**Trigger.** A tolerance-based row count check was introduced so that a flaky
source would not page anyone. The tolerance was wider than the defect.

**Blast radius.** Six daily files understated totals. Finance reconciled manually.

**Fix.** Parity is exact. The tolerance is gone.

**Probe that would have caught it.** A fixture with one deliberately dropped line;
the check must fail. Now a claim in the project ISA.
```

The rule extracted from an incident does not stay in the incident. It goes into the path-scoped instructions file or the relevant skill, citing the id. Incidents are the story; instructions are the enforcement.

## Recall a prior session

- `python -m kaios isa list` then `python -m kaios isa status <path>` names what was being built and how far it got.
- `python -m kaios memory search <term>` across the term you remember: a table name, a service, an error string.
- `python -m kaios memory digest --since <date>` when you know roughly when and not what.
- Read the found ISA's Decisions and Log before doing anything. That is where the dead ends are, and re-walking a dead end is the most expensive thing a resumed session can do.

## Constraints and gotchas

- Capture during the run, not at the end. A learning written twenty tool calls later has lost the detail that made it useful.
- Never capture a secret, a token, a connection string, or a customer identifier. There is no redaction pass downstream.
- A capture is one line. If it needs three paragraphs it is a knowledge note or an incident.
- Memory is advisory, never authoritative over the repository. When a note and the code disagree, the code is right and the note is stale: fix the note in the same turn.
- Do not mine the conversation for learnings at close as a ritual. Most runs learn nothing durable, and a system that writes a note every time teaches its readers to ignore notes.
