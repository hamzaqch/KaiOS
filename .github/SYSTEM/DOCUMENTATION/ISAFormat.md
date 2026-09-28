---
version: 1.0.0
last_updated: 2026-09-28T00:00:00Z
convention: kaios-freshness-v1
---

# ISA format

> The file-shape contract for an Ideal State Artifact. `python -m kaios isa check <path>` implements exactly this document; `python -m kaios isa scaffold` writes it; `python -m kaios isa frontier` reads the edges. When an implementation and this file disagree, this file is the specification and the implementation is the bug.

An ISA is one Markdown file: YAML frontmatter, then H2 sections in a fixed order. The model is the sole writer. Tools and hooks read it, mirror it, and gate on it, but never edit it — that is what keeps it a single source of truth rather than a file two systems fight over.

## Two homes

| Home | For | Path |
|---|---|---|
| Project ISA | anything with a persistent identity — a service, a library, a pipeline, this system | `<repo>/ISA.md` |
| Task ISA | one-off work that does not belong to a persistent thing — an investigation, a migration, a design session | `$KAIOS_HOME/MEMORY/WORK/<slug>/ISA.md` |

A project ISA outlives every run and is the thing's current state between runs. A task ISA is closed and kept as a record. Every ISA write mirrors to `MEMORY/STATE/work.json`.

## Frontmatter

```yaml
---
phase: climbing
progress: 3/8
task: "short description, about eight words"
slug: 20260928-140000_import-retry
started: 2026-09-28T14:00:00Z
updated: 2026-09-28T14:40:00Z
stated_goal: "the verbatim words of the ask, byte for byte"
iteration: 2
frozen: false
---
```

| Field | Required | Rule |
|---|---|---|
| `phase` | yes | one of `scoping`, `climbing`, `complete`. `scoping` while done is being articulated, `climbing` while building and verifying, `complete` at close. Nothing else is legal. |
| `progress` | yes | `M/N`, a mechanical count over the `ISC-N` claims. `N` is the number of live ones; `M` is how many of those are closed. Tombstoned claims and anti-claims are excluded from both. Never an opinion, never a percentage. |
| `task` | recommended | short prose description. Falls back to the H1 title when absent. |
| `slug` | recommended | `YYYYMMDD-HHMMSS_kebab-name` for task ISAs; falls back to the directory name. A project ISA may use the project name. |
| `started` | recommended | ISO 8601 with a `Z`. |
| `updated` | recommended | ISO 8601 with a `Z`. Rewritten on every write. |
| `stated_goal` | conditional | the verbatim ask. Never paraphrased, never corrected, never trimmed. Set it when the ask has real propositional content; use `null` when the literal was contentless ("make it better"). Immutable unless the ask is explicitly revised, and a revision is recorded in `## Decisions`. |
| `iteration` | conditional | integer, appears from the second run onward. Incremented when a completed ISA is reopened. |
| `frozen` | optional | `true` means a body edit does not reopen a completed ISA. Default `false`. |

Unknown keys are tolerated on read and never written. An empty section is never created as a placeholder.

## Sections, in fixed order

Each section appears only when it has content. The order below is the contract: `isa check` reports a section that appears out of order.

| # | Section | Holds |
|---|---|---|
| 1 | `## Problem` | what is broken or missing right now |
| 2 | `## Vision` | what the good outcome feels like to the person who asked — the experiential intent |
| 3 | `## Out of Scope` | prose anti-vision: what this deliberately does not include |
| 4 | `## Language` | the project's terms. One block per term: what it means, an `Avoid:` line naming the words it displaces, and any relation to other terms. A term enters only after it has actually caused a confusion, so this is a record of resolved collisions and never a speculative dictionary. Project ISAs only. |
| 5 | `## Principles` | truths the work must respect regardless of implementation |
| 6 | `## Constraints` | immovable mandates — platform, language, deployment, policy |
| 7 | `## Dependencies` | cross-ISA needs, one machine-readable line each: `requires: <slug> — <what and the contract>` |
| 8 | `## Goal` | one to three sentences naming verifiable done. The hard-to-vary spine. |
| 9 | `## Features` **or** `## Claims` | the claims. Use `## Features` when the work has distinct features, `## Claims` when it does not. Never both. |
| 10 | `## Not yet specified` | fog — in-scope questions too dim to state as claims yet |
| 11 | `## Anti-claims` | what must not happen, as claims. May instead live inline with an `Anti:` prefix. |
| 12 | `## Test Strategy` | one row per claim: the probe contract |
| 13 | `## Decisions` | dated decisions including the dead ends |
| 14 | `## Log` | the run trail and one provenance stub per closed claim |
| 15 | `## Remaining Work` | concrete work this ISA still owes that was never a claim of this run |

### Which sections are required

Scaled to the substance of the work, discovered from the work rather than predicted:

| Substance | Required |
|---|---|
| Trivial — mechanical, one probe, minutes | `## Goal`, `## Claims` |
| Substantial — multi-claim build with real blast radius | `## Problem`, `## Vision`, `## Out of Scope`, `## Constraints`, `## Goal`, claims, `## Test Strategy` |
| Frontier — multi-component work | all fifteen that have content, with a scoping interview before building |

A project ISA is always held to the substantial bar regardless of how small today's task is. `## Dependencies` is required when the ISA has cross-ISA needs and omitted otherwise. `## Language` is never required by substance. `## Remaining Work` is never required and never gated — a mandatory version would manufacture make-work.

### Feature blocks

When the work has distinct features, `## Features` holds them as blocks:

```markdown
## Features

### F0 · Cross-cutting
Why: invariants that hold across every feature — security, packaging, data integrity.

- [x] ISC-1: No module imports outside the standard library. Falsifier: an import scan reports a third-party module.

### F1 · Ingest
Why: a malformed upstream row costs one row, never the run.

- [x] ISC-2: A malformed row lands in the reject table with its parse error. Falsifier: a seeded bad row is absent from rejects.
- [ ] ISC-3: The job exits zero when every row rejected. Falsifier: non-zero exit on an all-bad fixture. (after: ISC-2)
```

- `F0` is reserved for cross-cutting claims. Feature blocks are `F1`, `F2`, and so on, in build order.
- The `Why:` line is the feature's ideal state in one sentence. A `Why:` that restates the feature name carries no information and gets cut.
- **Claim IDs are global and sequential across the whole ISA**, never per-feature. Moving a claim between features never renumbers it.
- Feature numbers are display order, not identity. Reordering blocks is free.

## Claim syntax

```
- [ ] ISC-7: The retry backoff caps at sixty seconds. Falsifier: a forced failure sleeps longer than 60s. (after: ISC-4, ISC-5)
```

The line grammar, in the order a parser should strip it:

1. **The line.** `^\s*- \[( |x|X)\] (ISC-\d+(\.\d+)*): (.+)$` — checkbox state, identifier, colon-space, body. Indentation is allowed for nested claims.
2. **The evidence stub**, when the claim is closed. Split the body on the last occurrence of ` — evidence: `. What follows is the stub.
3. **The edge**, optional. On what remains, match `\((?:after:\s*)([^)]*)\)\s*\.?\s*$` — the edge is the *last* parenthetical of the claim body. A mid-body parenthetical and anything inside backticks never parse as an edge, so a claim can quote the syntax safely.
4. **Statement and falsifier.** Split what remains on the first `Falsifier:` (that exact spelling, case-sensitive). Before it is the statement, after it is the falsifier.

Rules:

- **Every live claim names a falsifier.** A claim with no `Falsifier:` is a check failure, not a style note. If you cannot say what would prove it false, it is not a claim yet — it is fog.
- The statement describes an **end state**, not an action. "The reject table receives malformed rows", not "add reject handling".
- **Atomic**: one verifiable thing per claim. Apply the splitting test below.
- Check the box the moment the claim is satisfied. Do not batch checks at the end, and update `progress` on every change.
- Nested claims use `ISC-N.M` and markdown indentation. The falsifier requirement applies at the leaves; a parent is an aggregation that holds when all its leaves hold.

### Anti-claims

At least one anti-claim is required on every ISA. A goal with no failure mode worth naming is under-specified.

Anti-claims have their own identifier namespace, `A<n>`, so they never consume `ISC-N` numbers and a reader can tell the two kinds apart at a glance. They live in `## Anti-claims`:

```markdown
## Anti-claims

- A1: No credential value is ever written to a log line. Falsifier: a secret-shaped string appears in captured output.
- A2: No module imports outside the standard library. Falsifier: the import scan reports a third-party module.
```

Three spellings are recognised, and any of them satisfies the requirement: an `- A<n>:` bullet anywhere, a bullet whose text begins `Anti:`, or any claim bullet inside a section whose name contains "anti". The `A<n>` form in `## Anti-claims` is the one to write.

An anti-claim carries a falsifier like any other claim, may be checked and carry an evidence stub, and may be referenced from `## Test Strategy`. It is excluded from `progress`, which counts `ISC-N` claims only.

### Dependency edges and the frontier

When claims have real execution ordering, put it on the claim line as the last parenthetical: `(after: ISC-1, ISC-2)`. Identifiers are claim IDs from the same ISA. Edges are intra-ISA only; cross-ISA needs live in `## Dependencies`.

A claim is **takeable** when it is open, not tombstoned, and every `after:` blocker is resolved — checked or dropped. The **frontier** is the set of takeable claims: what can be worked right now. `python -m kaios isa frontier <path>` computes it.

Edges are optional forever. No gate requires them, counts them, or rewards them. Encode ordering that is real; a fully-edged ISA whose work was actually parallel is decoration. `isa check` reports cycles, unknown identifiers, self-references and duplicates loudly.

### Tombstones

A claim that is dropped leaves a tombstone. It never vanishes and it never gets renumbered:

```markdown
- [ ] ISC-9: [DROPPED: superseded by ISC-14 after the schema change]
```

The state stays `[ ]`, the body starts with `[DROPPED:` and carries a reason before the closing bracket. A tombstoned claim needs no falsifier, is excluded from both halves of `progress`, and counts as resolved for the purpose of `after:` edges.

### The ID-stability rule

**Claim identifiers are append-only and never renumber.** This is what lets `## Test Strategy`, `## Log`, `## Decisions`, git history, and every prior reference stay valid across edits.

- A claim that turns out to hide two failure modes **splits**: the parent is preserved as a container and the halves become `ISC-N.1` and `ISC-N.2`.
- A claim that is no longer wanted becomes a **tombstone**, not a deletion.
- A claim of this run that simply is not done yet stays an unchecked claim. It does not move to `## Remaining Work`.

### Evidence stubs on close

The moment a claim goes `[x]`, its evidence collapses to a one-line pointer appended to the claim line:

```
- [x] ISC-2: A malformed row lands in the reject table. Falsifier: a seeded bad row is absent from rejects. — evidence: pytest tests/test_ingest.py::test_reject_row
```

The stub is a commit hash, a test identifier, a command, or a probe reference. Never a retained paragraph — the proof lives in git and in the test run, and the ISA only has to point at it. `## Log` may carry the same stub keyed by claim ID. A closed claim with no stub anywhere is a check failure and the Stop gate blocks on it.

## Fog: `## Not yet specified`

One line each: `- fog: <the question, as precisely as it can be stated today> — <what must resolve before it sharpens>`.

**The test — fog or claim?** *Can you state the question precisely right now — not answer it, state it?*

- Sharp enough to name its falsifier → a claim, even if it is blocked.
- Statable but not yet probe-able → a fog entry.
- Outside what we are building at all → `## Out of Scope`.

Fog graduates. When work sharpens an entry, it becomes a claim, or it becomes a `## Decisions` row that kills it, and it leaves this section either way. Fog is never checked, never counted in `progress`, and never verified.

## Coverage, assessed at close

There is no minimum claim count. Counts reward splitting theatre — atomising to reach a number instead of to reach a probe.

The gate is **coverage**: every subsystem named in `## Vision` or `## Goal` has claims, and every claim decomposes until each leaf is one binary probe. A 20-claim ISA passes if it covers the surface. A 200-claim ISA fails if a named subsystem has none.

Coverage is assessed **at close, not at scaffold**. A subsystem whose shape is genuinely unknown at the start is not covered by inventing speculative claims for it — it is held as fog and graduates as pursuit sharpens it. Writing claims you cannot yet state precisely, in order to look complete early, is exactly the failure the fog section exists to prevent. At `phase: complete` the gate is strict: every named subsystem has real coverage, and the fog section is empty.

## The splitting test

Apply to every claim:

- Does it join two verifiable things with "and", "with", or "including"? → split.
- Can one half pass while the other fails? → split.
- Does it say "all", "every", or "complete"? → enumerate what that means.
- Does it cross a boundary — interface, data, orchestration, packaging? → one claim per boundary.
- Does it change a shared symbol or a generated artifact? → enumerate the consumers, one probe each. One stale consumer means the whole class is suspect.

Split until each leaf is one binary probe, then stop. If you cannot name the probe, the claim is not atomic yet.

## `## Test Strategy`

One row per claim. Column order is the parser contract:

```markdown
| isc | type | check | tool | anchors_to |
|---|---|---|---|---|
| ISC-2 | pytest | a seeded bad row appears in rejects | pytest tests/test_ingest.py -k reject_row | literal |
| ISC-3 | command | all-bad fixture run exits 0 | python -m jobs.ingest --fixture all_bad | derived: exit-contract |
```

`type` is a closed vocabulary, one per verification modality:

| `type` | Closes on |
|---|---|
| `file` | reading the file back |
| `grep` | a search whose output was read |
| `command` | a command's real output and exit code |
| `pytest` | a named test passing |
| `http` | `curl -i` against the real URL |
| `sql` | a `SELECT` that returned rows |
| `screenshot` | an image that was looked at |
| `manual` | a person says yes on encounter |

`anchors_to` is `literal` when the claim traces straight to `stated_goal`, or `derived: <name>` when it traces through a named derivation. Backticks around a `tool` value are stripped as formatting. A row whose `isc` does not match a claim, and a live claim with no row, are both check failures.

## What `isa check` enforces

Hard failures, exit 1:

1. `phase` missing, or not one of the three legal values.
2. `progress` missing, or not in `M/N` form.
3. No `## Goal` section — the outcome is not written down.
4. No claims at all.
5. Zero anti-claims.
6. A live claim with neither a `Falsifier:` nor a `## Test Strategy` row.
7. A duplicated claim identifier, or identifiers that do not increase down the file.
8. An `after:` edge naming an unknown identifier, forming a cycle, or pointing at itself.
9. A section appearing out of the fixed order, or both `## Features` and `## Claims` present.
10. A `## Test Strategy` row whose first column matches no claim, or a `type` outside the vocabulary.
11. A tombstone with no reason inside its brackets.
12. Writing `phase: complete` while `## Not yet specified` still has entries.

Warnings, reported and not blocking: `progress` disagreeing with the mechanical count, and a closed claim with no evidence stub. Both are hard at the Stop gate rather than here, because `isa check` runs mid-build when a count is legitimately in flux for a moment, and the close is where it must be exact.

Advisory findings, reported and never blocking: a live claim with no `## Test Strategy` row, a claim whose statement fails the splitting test, a named subsystem with no claims, a `Why:` line that restates its feature name, and a `stated_goal` that is absent on substantial work. These are judgment calls, and a count that blocks is a count that gets manufactured.

## A canonical ISA

The whole file, for a small task — adding a `--json` flag to an internal tool — shown closed.

```markdown
---
phase: complete
progress: 2/2
task: "add --json output to the report tool"
slug: 20260928-093000_report-json
started: 2026-09-28T09:30:00Z
updated: 2026-09-28T10:05:00Z
stated_goal: "make the report tool able to emit json so the scheduler can parse it"
---

# Report tool JSON output

## Goal
The report tool accepts `--json` and prints one valid JSON object carrying the same
data as its text output, and the default text output is byte-identical to before.

## Claims
- [x] ISC-1: `--json` prints exactly one object that parses as JSON. Falsifier: the output fails a JSON parse. — evidence: pytest tests/test_report.py::test_json_parses
- [x] ISC-2: The JSON carries every field the text output shows. Falsifier: a field present in text is missing from JSON. (after: ISC-1) — evidence: pytest tests/test_report.py::test_field_parity

## Anti-claims
- [x] A1: The default text output changes. Falsifier: a diff against the saved baseline is non-empty. — evidence: 4f1c2ab

## Test Strategy
| isc | type | check | tool | anchors_to |
|---|---|---|---|---|
| ISC-1 | command | output parses as one JSON object | python -m report --json \| python -m json.tool | literal |
| ISC-2 | pytest | field sets are equal | pytest tests/test_report.py -k field_parity | literal |
| A1 | command | diff against baseline is empty | python -m report > out.txt && diff out.txt tests/fixtures/report.txt | derived: text-parity |

## Log
- 2026-09-28: ISA scaffolded, two claims and one anti-claim. Baseline captured before the flag landed.
```

Everything the spec requires is present and nothing it forbids is: minimal frontmatter with no invented keys, `progress` as a mechanical count over the `ISC-N` claims, an anti-claim in its own `A<n>` namespace, a falsifier on every claim, an evidence stub on every closed claim, one probe row per claim, and no empty placeholder sections.
