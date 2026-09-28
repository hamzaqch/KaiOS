---
version: 1.0.0
last_updated: 2026-09-28T00:00:00Z
convention: kaios-freshness-v1
---

# Memory

> Everything that changes at runtime lives under `$KAIOS_HOME` and is never committed. The repository holds the system; this tree holds what the system learned and what it is currently working on.

## Layout

```
$KAIOS_HOME/                       default ~/.kaios
  CONFIG/config.json               what setup detected plus your choices
  CONFIG/models.json               your copy of the role registry
  USER/PROFILE.md                  work profile from the setup interview
  USER/PROJECTS.md                 project table and routing aliases
  SYSTEM/                           installed doctrine copy
  MEMORY/
    STATE/work.json                the ISA registry
    STATE/hot.md                   the hot layer
    STATE/isa-locks/               per-claim locks for concurrent sessions
    WORK/<slug>/ISA.md             task ISAs
    KNOWLEDGE/*.md                 reusable facts, typed frontmatter
    LEARNING/REFLECTIONS/*.jsonl   one line per run that did real work
    LEARNING/INCIDENTS/*.md        dated failure narratives
    OBSERVABILITY/hook-events.jsonl
    OBSERVABILITY/tool-events.jsonl
    OBSERVABILITY/ask-fidelity.jsonl
```

Project ISAs do not live here. They stay in their own repository at `<repo>/ISA.md`, because a thing with a persistent identity keeps its state of record beside its code.

## The hot layer

`MEMORY/STATE/hot.md` is the small, bounded file that `SessionStart` injects: what is currently in flight, what changed recently, and anything a session would otherwise have to rediscover. It is deliberately short — a hot layer that grows becomes a context tax paid on every single session, including the ones that did not need it.

Its content is derived, never hand-maintained. The work registry, the most recent reflections, and the open claims of the active ISA are what it is built from, so it cannot drift out of agreement with them.

## WORK

One directory per task, named by slug, holding that task's ISA and nothing else that matters. The ISA is the state of record: what done means, which claims hold, what the evidence was, what was decided, and what is still owed. Format: `ISAFormat.md`.

Resume reads the ISA, never the conversation. That is what makes it safe to close a long session and start a clean one instead of pushing a degraded context through a compaction.

Every ISA write mirrors to `MEMORY/STATE/work.json`, which is a single JSON object keyed by slug:

```json
{
  "20260928-093000_report-json": {
    "path": "MEMORY/WORK/20260928-093000_report-json/ISA.md",
    "task": "add --json output to the report tool",
    "phase": "complete",
    "progress": "3/3",
    "started": "2026-09-28T09:30:00Z",
    "updated": "2026-09-28T10:05:00Z",
    "iteration": 1
  }
}
```

The registry is a mirror and never an authority. When it disagrees with a file on disk, the file wins and the registry is rebuilt. `python -m kaios isa list` reads the registry; `python -m kaios memory health` is what notices a disagreement.

## KNOWLEDGE

Reusable facts, one Markdown file each, with typed frontmatter so the archive stays queryable instead of becoming a folder of notes:

```yaml
---
type: platform                 # platform | codebase | domain | tool | rejected
title: Bundle validation exit codes
tags: [databricks, ci]
added: 2026-09-28T00:00:00Z
sources: ["command output 2026-09-28"]
---
```

What belongs here: a fact about the platform that took work to establish, a non-obvious contract in the codebase, a domain rule, a tool's real behaviour as opposed to its documented behaviour. What does not: anything about how to work — that is doctrine or a skill — and anything about one task, which is that task's ISA.

`type: rejected` is its own case. A proposal that was deliberately turned down gets a file saying what it was and why, because the same proposal arrives again six weeks later looking new. Check knowledge before re-analysing a familiar-smelling idea.

`KnowledgeWriteGuard` requires the frontmatter. An untyped note is a note nobody will find.

## LEARNING

**Reflections** are one JSON line per run that did real work, appended to `LEARNING/REFLECTIONS/<YYYY-MM>.jsonl` by `python -m kaios memory capture --kind reflection`:

```json
{"ts":"2026-09-28T10:05:00Z","session":"…","slug":"20260928-093000_report-json","kind":"reflection","reflection":"Reached for the fixture diff before capturing a baseline; the baseline should have been claim one.","claims_closed":3,"claims_open":0,"second_look":"skipped: local, no shared surface"}
```

The self-critique is the payload — what a smarter run would have done differently. Operational fields are derived by the tool. Nothing here is a self-assigned score, because a score is a number a model will learn to produce rather than earn.

**Incidents** are dated narratives for a failure worth keeping as a signal: `LEARNING/INCIDENTS/INC-YYYYMMDD-<slug>.md`, with what happened, what was believed at the time, what actually was true, and what changed as a result. The story lives there only; a rule that came out of an incident cites the identifier rather than retelling it. That is what keeps doctrine from turning into a history book.

## OBSERVABILITY

Three append-only JSON Lines streams. Append-only is the point: a stream that gets rewritten cannot be trusted as a record of what happened.

`hook-events.jsonl` — the raw event every hook dispatch received, plus any module exception:

```json
{"ts":"2026-09-28T09:31:02Z","event":"PreToolUse","session":"…","tool":"terminal","raw":{…}}
{"ts":"2026-09-28T09:31:02Z","event":"PreToolUse","module":"SecretsGuard","error":"KeyError: 'command'","traceback":"…"}
```

Writing the raw event before dispatching is deliberate. It means the real schema of each event is discoverable from actual runs, so hooks can stay tolerant instead of guessing.

`tool-events.jsonl` — one line per tool call and outcome:

```json
{"ts":"2026-09-28T09:31:03Z","session":"…","tool":"terminal","ok":true,"ms":412,"summary":"pytest tests/test_report.py"}
```

`ask-fidelity.jsonl` — one line per run, recording whether every explicit ask was met:

```json
{"ts":"2026-09-28T10:05:00Z","slug":"20260928-093000_report-json","asks":[{"ask":"emit json","status":"met"},{"ask":"don't change text output","status":"met"}],"unmet":0}
```

## The CLI

| Command | Does |
|---|---|
| `memory capture --kind K --text T` | append a record — `reflection`, `knowledge`, `incident`, `note` |
| `memory search Q` | substring and tag search across knowledge, work, and reflections |
| `memory digest [--since D]` | what happened over a window, from the streams |
| `memory health` | registry against disk, stream readability, hot-layer size, orphaned work directories |
| `memory knowledge add` / `find` | write or query a typed knowledge file |

## What memory is not

It is not a place to record rules. A rule written as a note depends on someone finding the note; the same rule in doctrine, an `applyTo` file, or a hook is in force whether anyone remembers or not. Routing table: `../RULES/SelfHealing.md`.

It is also not a transcript archive. The streams record what tools did and what was learned. The conversation is not a source of truth about what closed — the ISA is.
