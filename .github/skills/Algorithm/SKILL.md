---
name: algorithm
description: "Runs a unit of work against an ideal state instead of against a vibe: load the doctrine, write done down as claims, take the frontier, close each claim on tool evidence of the right modality, check every explicit ask was met, elect a second look from a different model family, and close in the KaiOS response format. USE WHEN build this, implement, ship, fix, refactor, migrate, run the algorithm, work this task, take the next claim, hill-climb, resume, pick up where we left off, continue the build, how should I approach this, this is bigger than one command. NOT FOR writing or repairing the ISA itself (use isa), a single factual question or a one-line edit that needs no plan, grading output quality across samples (use evals), or reviewing someone else's diff (use pr-review)."
argument-hint: "<goal>"
---

# Algorithm — how work gets done here

## What this produces

A unit of work that ends with an ISA whose closed claims each point at evidence, a repository in a state a teammate can verify without asking, and a response in the KaiOS format that shows what changed and what proves it.

The doctrine itself is not in this file. It lives at `$KAIOS_HOME/SYSTEM/ALGORITHM/` — read `LATEST`, which holds a version string, then read that version's file. Read it before planning anything that will take more than one command. The version file is the authority; this skill is how to run it inside Copilot.

## Done looks like

- An ISA exists at the right home and was written before the first mutation.
- `python -m kaios isa check <path>` exits 0.
- Every claim that moved to `[x]` carries a one-line evidence stub naming a probe that actually ran.
- Every explicit request in the original message was met, or skipped with a stated reason in the Log.
- Any independent review's findings are dispositioned in the ISA: adopted with a diff, rebutted with a reason, or deferred as named work.
- The closing response carries the answer, the change, and the verification.

## USE WHEN

The work has more than one moving part, a build is starting, a session is resuming, or something has to be true afterwards that a reader could check.

## NOT FOR

Authoring or repairing the ISA (`isa`). Trivial single-command work. Multi-sample quality grading (`evals`). Reviewing a diff you did not write (`pr-review`).

## The loop

1. **Frame.** Restate the goal in one sentence and keep the original wording somewhere it cannot be edited: the ISA's stated-goal field. Everything later is measured against that string, not against your restatement.
2. **Articulate done.** Write or update the ISA. Claims with falsifiers, at least one anti-claim, fog named rather than guessed. For a task that genuinely fits in one file, a Goal plus Claims ISA is enough; for anything persistent, use the full section order.
3. **Probe prerequisites.** Tokens, logins, CLI presence, deploy targets, network reach. Probe before building, not at the end. Missing blocks or is written into the Log as a ratified deferral. Unknown is surfaced and never blocks.
4. **Resolve ambiguity.** At most three questions, each one whose answer would change what gets built. If a reasoned default is safe, state the assumption inline and continue. Never infer a referent you have not seen: a named file, table, job or document gets found on record before anything is built on top of it.
5. **Take the frontier.** `python -m kaios isa frontier <path>` returns the claims whose prerequisites are closed. Take one, or take a small independent set in parallel. Do not take a claim that is blocked; close its blocker first.
6. **Close on evidence.** Each claim closes only on tool output of the matching modality, produced in this turn or the last. Append the stub and flip the box. "Should work" is not a state that exists.
7. **Sweep the class.** When a defect turns out to be an instance of a pattern, enumerate the siblings with one search before closing, then fix or tombstone each. Report the class, the probe, and the counts.
8. **Close the run.** Check ask fidelity, elect or skip a second look with the reason recorded, fold what was learned into the ISA and memory, and answer in the response format.

## What makes a run complete

| Claim | How it holds |
|---|---|
| Goal preserved | the stated goal is byte-identical to what was asked; claims trace to it |
| Done written first | the ISA predates the first mutation |
| Anti-claims present | at least one thing that must not happen, with its probe |
| Prerequisites probed | external dependencies checked before execution, not after |
| Ambiguity resolved | material questions asked, or a default stated inline |
| Evidence per claim | right modality, same or next tool block, one-line stub |
| Class sweep | a defect's siblings enumerated by a search before close |
| Ask fidelity | every explicit request met, skipped with a reason, or surfaced |
| Second look | elected and dispositioned, or skipped with the reason logged |
| Trail | decisions, dead ends and remaining work land in the ISA |
| Spend | depth, parallelism and model rung matched the blast radius |

## Evidence modality

A claim closes on the kind of evidence its subject can actually produce.

| Claim about | Closes on |
|---|---|
| a file's contents | reading the file back after the write |
| a pattern across a tree | a search whose output you read |
| a command working | that command's output and exit code |
| a test passing | the runner's output naming the test |
| a schema or a table | a query result |
| a job or a deploy | the platform's own status for that run |
| config | reading the applied config back from the thing that consumes it |
| behaviour or quality | a repeated eval, not a single lucky sample |

Two failure modes to watch. Evidence must **span** the claim: a green suite is never evidence for one function inside it. Evidence must **arrive when the failure can exist**: a probe against a warm cache proves nothing about the authority behind it.

## Ask fidelity

Before closing, reread the original message and walk its explicit requests one at a time. Each is met, skipped with a stated reason, or surfaced as still open. A depth instruction is an explicit request: "go deep", "quick pass", "don't touch the tests" all count, and answering a heavy ask inline with no visible work is a break that gets named, not hidden. Scope narrows only where the engineer agreed to narrow it.

## Second look

The builder does not grade the build. It will defend its own code, and it shares the blind spots of whatever produced it.

- Dispatch the **Reviewer** agent (max role, fresh context) for an in-family skeptic pass, carrying the ISA and the original goal.
- Dispatch the **Auditor** agent (cross role, read-only) for a second look from a different vendor family. A cross-family read catches the errors a same-family reviewer agrees with.
- The rule: a second look is always a different family from whatever built the thing.
- Scale the choice to blast radius. For a scratch script, skipping review is fine. For anything touching auth, data deletion, a shared surface, or something other teams depend on, skipping it requires one Log line naming the skip and why. Silent skipping is the thing that is banned, not skipping.
- Contradictions between reviews get surfaced, never quietly resolved. Two clarifying rounds, then bring it to the engineer.

## Resume

A resumed session reads the ISA and the repository. It does not read the conversation, because the conversation is the least reliable record in the system and may not exist any more.

- `python -m kaios isa list` finds the ISA, `status` gives phase and progress, `frontier` gives what is takeable.
- `python -m kaios memory digest` gives what recent runs learned.
- Verify the last closed claim's evidence still holds before trusting it. A stub that names a test is worth re-running; a stub that names a commit is worth reading.
- Only then continue. Never re-derive a decision already recorded in Decisions; if you disagree with it, say so and let it be revisited explicitly.

## Spend

Match intelligence and verification depth to what the work turns out to be, and say so when they diverge.

- Judgment, design, planning, review, audits and meta work on KaiOS itself run at the **max** rung.
- Scoped execution runs at **high**. Formatting, renames and mechanical edits run at **medium**.
- A second opinion runs at **cross**, a third vendor's read or a very long context at **third**, and web or document research at **research**.
- The engineer's plain-language instruction outranks all of this. "Quick pass" means quick.
- Never name a model in prose. Roles are the vocabulary; `.github/SYSTEM/CONFIG/models.json` holds the lineup and `python -m kaios models apply` propagates it.

## Tool contracts

<!-- keep: tool-contract -->

| Command | Contract |
|---|---|
| `python -m kaios isa frontier <path>` | the claims takeable now, prerequisites satisfied |
| `python -m kaios isa check <path>` | syntax and completeness gate; non-zero blocks close |
| `python -m kaios isa status <path>` | phase and progress for the response's verify block |
| `python -m kaios memory capture --kind K --text T` | one line into the hot layer during the run |
| `python -m kaios memory digest` | what recent runs learned, for resume and for review |
| `python -m kaios doctor` | environment self-check when something behaves oddly |

## Constraints and gotchas

- Reproduce a reported defect before reading the suspect code. The fastest wrong fix in the world is the one aimed at the wrong file.
- Do not soften a claim to close it. Split it, tighten it, or drop it with a reason.
- Do not let the ISA become a changelog. Version control is the change record.
- Analysis is read-only. A request to look at something, explain it, or review it does not license an edit.
- Restore parity when replacing anything live: capture the baseline before the change, prove the flow's rate afterwards. One synthetic success is an example, not parity.
