---
name: red-team
description: Adversarial stress test of an idea, plan, design, estimate, or claim set. Breaks the target into atomic claims, attacks each one through parallel lenses (evidence, incentives, failure modes, security, operations, cost, second-order effects), steelmans the strongest objection against you, then reports severity-ranked findings with concrete remediation. USE WHEN red team, attack this, break this, find the holes, poke holes, what could go wrong, critique this plan, devil's advocate, strongest objection, stress test, pre-mortem, worst case, before shipping something risky, convince me this is wrong. NOT FOR collaborative deliberation among viewpoints hunting the best path (use council), tracing why a failure already happened (use root-cause-analysis), auditing an instruction set for bloat (use bitter-pill), or writing the plan in the first place.
argument-hint: "<the idea, plan, file, or diff to attack>"
---

# Red Team

Attack a thing on purpose so its weaknesses surface here instead of in production.

## USE WHEN / NOT FOR

USE WHEN you need a proposal, plan, estimate, or design attacked before it ships, or when someone asks for the strongest objection to their own idea.

NOT FOR collaborative deliberation looking for the best path, which is council, or tracing a failure that already happened, which is root-cause-analysis. It does not write the plan it attacks.

## What this produces

A findings report whose every row is an attack that a competent skeptic could actually make, ranked so the reader knows what to fix first.

## Done looks like

Every one of these is true and checkable by reading the output.

- Every load-bearing claim in the target appears as its own numbered row. A claim is atomic when it can be true or false on its own.
- Every finding names the lens that produced it, so no lens silently did nothing.
- Every finding carries a severity and a remediation that a builder could start on today. "Consider revisiting" is not a remediation.
- The strongest objection to the target has been stated in its most persuasive form, then answered or conceded.
- Findings that turned out to be wrong on inspection are listed as dismissed with the reason, not deleted. Silent deletion hides the work.

The measure of a good pass is not finding count. It is whether the target owner changes something after reading it.

## Output contract

Open with a one-paragraph verdict: is the target sound, sound with fixes, or structurally broken. Then the findings table, exactly these columns.

| # | claim | attack | severity | remediation |
|---|-------|--------|----------|-------------|

Severity uses four values only.

| severity | meaning |
|---|---|
| critical | the target fails at its stated purpose, or causes data loss, outage, or an unrecoverable commitment |
| high | a core claim is unsupported and the plan probably needs reshaping |
| medium | a real gap with a known workaround or a bounded blast radius |
| low | a rough edge, a naming problem, a missing note |

After the table add two short sections. **Steelman** states the best case for the target in the words of its strongest advocate, then says whether that case survives the critical and high findings. **Dismissed** lists attacks that were considered and rejected, one line each with the reason.

## Attack lenses

Run several lenses over the same claim set rather than one long pass. Each lens asks a different question, which is why they find different things.

| lens | the question it asks |
|---|---|
| evidence | what actually supports this claim, and would that evidence convince someone who wanted it to be false |
| assumptions | which unstated belief has to hold, and what happens the first time it does not |
| failure modes | what breaks under load, at the boundary, on retry, on partial success, when a dependency is slow |
| security | who benefits from abusing this, what do they need, what is the cheapest abuse |
| operations | who gets paged, what do they see, can they tell what went wrong and roll it back |
| data | what happens to correctness when inputs are late, duplicated, out of order, or malformed |
| cost and time | what is the real cost at real volume, and what is the estimate missing |
| incentives | whose interests does this serve, and what behavior does it reward that nobody intended |
| second order | if this works perfectly, what does it make worse elsewhere |
| alternative | what simpler thing gets most of the benefit, and why was it not chosen |

Pick the lenses that fit the target. A pricing plan does not need a retry-semantics lens; a queue consumer does. Say which lenses you skipped and why, in one line.

## Roles

Run the decomposition and the attacks at the **max** role, because severity judgment is the whole value. Send a second pass to the **cross** role, a different vendor family from whoever produced the target, when the target was itself written by a model. A builder grading its own work shares its own blind spots. Copilot's agent picker and the Auditor agent carry the routing; never name a model in the report.

## Constraints and gotchas

- Attack the claim, never the author. There is no person in a findings table.
- An attack without a mechanism is a mood. "This won't scale" is not a finding; "the join fans out per event and the table grows daily, so p99 doubles by quarter end" is.
- Do not attack a claim the target never made. Quote or paraphrase the claim as written before attacking it.
- Read the target before attacking it, including the code or config it points at. Attacking a summary invents findings.
- Stay read-only. This skill reports; it does not edit the thing it attacks. Handing the findings to a builder is the next step, not part of this one.
- If the target is too vague to decompose, say so and name the three questions that would make it attackable. A red team on fog produces fog.
