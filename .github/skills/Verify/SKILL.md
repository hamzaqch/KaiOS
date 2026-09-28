---
name: verify
description: "Closes claims on evidence instead of on confidence. Names the modality a given claim can actually close on, catches the six ways verification lies (wrong modality, appearance mistaken for existence, a fix never reproduced, a probe fired before the failure could exist, lost prior behaviour, a warm cache answering for the authority), and audits an ISA for checked boxes with no evidence stub. USE WHEN verify, verification, prove it, is it actually done, close this claim, what evidence do I need, evidence stub, did that really work, it says done, check the ISA evidence, I think it works, should work, appears to work, confirm the deploy, prove the fix. NOT FOR building the thing (use algorithm), grading quality across many samples (use evals), strengthening a test suite (use hardening), or diagnosing a failure's cause (use root-cause-analysis)."
argument-hint: "[claim or ISA path]"
---

# Verify — evidence, not confidence

## What this produces

For a claim about to close: the modality that can actually close it, the command or read that produces that evidence, and a one-line stub for the ISA. For an ISA: the list of claims whose boxes are checked with nothing behind them.

## Done looks like

- Every closed claim in the ISA carries a stub naming a probe that ran.
- `python .github/skills/Verify/evidence_check.py <ISA.md>` exits 0.
- No response says a thing works without output in the transcript showing it works.
- Where a verifier genuinely does not exist, the claim is marked deferred with the follow-up named, not quietly closed.

## USE WHEN

A claim is about to flip to done, a response is about to make a factual assertion about the system, an ISA needs auditing, or someone said "should work".

## NOT FOR

Building (`algorithm`). Multi-sample quality grading (`evals`). Hardening a suite (`hardening`). Root cause work (`root-cause-analysis`).

## Modality fidelity

The first rule, and the one broken most often. Evidence has to be of the kind the claim's subject can produce. A claim about a file does not close on a claim about a file.

| Claim about | Closes on | Does not close on |
|---|---|---|
| a file's contents | reading the file back after writing | the write command's exit code |
| a symbol or pattern across a tree | a search whose output you read | your memory of the layout |
| a command working | that command's own output and exit code | a similar command working |
| a test passing | the runner naming that test | the suite being green |
| an installed tool | the tool's own version output | the installer's success message |
| a schema, table or grain | a query result | the documentation |
| applied config | reading it back from the process that consumes it | the file you wrote |
| a scheduled job | the platform's status for that specific run | the schedule existing |
| behaviour or quality | a repeated eval across samples | one good sample |
| a path being absent | an explicit listing that shows it gone | the delete command succeeding |

## The five other ways verification lies

**Appearance is not existence.** A page that renders, a table that lists, a log line that prints: each proves a surface, not the thing behind it. A list endpoint returning `200` with an empty array is a working endpoint and a missing record. Check the content, not the shape.

**Reproduce before fixing.** Read the failing behaviour with your own probe before reading the suspect code. A defect report names a symptom and a guess; the guess is wrong often enough that acting on it first is the single most expensive habit available. If it cannot be reproduced, that is a finding, not an obstacle.

**Temporal fidelity.** A probe fired before the failure could exist proves nothing. Deploys propagate, caches fill, jobs queue, indexes build, DNS settles. Ask when the failure mode becomes possible and probe after that, not at T plus zero.

**Cache fidelity.** A special case worth its own name because it fools everyone. When state is cached anywhere between you and the source, the probe must reach the authority: bypass the cache, query the origin, or invalidate first. A warm-cache read tells you what the cache remembers.

**Restore parity.** When work replaces, reroutes or removes something that was already serving traffic or producing a number, the claim is not "the new thing works" — it is "the old behaviour is intact or better". Capture the baseline **before** the change. Afterwards, prove the flow's rate against that baseline, within a stated tolerance. A single synthetic event succeeding is an example, never parity; a pipeline can pass an end-to-end probe while running at a fraction of its old volume.

**Evidence has to span the claim.** A container passing is never evidence for its members. "The suite is green" does not close a claim about one function, and one region healthy does not close a claim about the fleet. Either probe each member or narrow the claim to what you actually checked.

## When there is no verifier

Sometimes the probe genuinely cannot run: no access, a nightly cadence, a dependency not yet provisioned. That is a state, not a failure, and it has one honest expression:

- Leave the claim open and write `[DEFERRED-VERIFY]` with the reason and the probe that will run.
- Name the follow-up in the ISA's Remaining Work.
- Say so in the response. An unverifiable claim reported as verified is worse than no claim.

The forbidden move is closing it because it looks right. "Should work" is not a verification state. Write "verified" with the evidence, or "not verified" with the reason.

## Tool contracts

<!-- keep: tool-contract -->

| Command | Contract |
|---|---|
| `python .github/skills/Verify/evidence_check.py <ISA.md>` | lists claims marked `[x]` with no `— evidence:` stub, plus stubs too short to name a probe. `--json` for machine output, `--falsifiers` to also flag claims with no falsifier. Exit 0 clean, 1 findings, 2 unreadable input. |
| `python -m kaios isa check <path>` | the wider gate: sections, id stability, ordering edges, falsifiers. |
| `python -m kaios isa status <path>` | progress numbers for a response's verify block. |

The two tools disagree on exit code by design, and the difference is the useful part. `isa check` reports a closed claim with no stub as a warning and does not fail, because a missing stub is a prompt to record evidence rather than a malformed ISA. `evidence_check.py` exits 1 on the same condition, because it is asked that one question and a non-zero answer is what a gate reads. The session-stop gate is where it actually blocks a close.

The stub is one line and it points, it does not prove. A test name, a commit hash, a command, a query, a path. The proof stays in the test suite, in CI, and in version control, and the ISA is the index.

## Constraints and gotchas

- The evidence must be in this turn or the one before it. Evidence from twenty tool calls ago describes a system that has since changed.
- Never accept your own summary of a tool's output as the evidence. Read the output.
- A hook that gates on evidence stubs will block a close that skipped this skill. That is the design, not a bug: fix the stub rather than routing around the gate.
- An empty result is ambiguous until you prove the probe can return non-empty. Run it against a known-present case first.
- Verifying is read-only. Finding a defect while verifying does not license fixing it in the same breath; report it, then decide.

