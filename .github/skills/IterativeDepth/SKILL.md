---
name: iterative-depth
description: Deliberate multi-pass review where each pass looks at the same artifact through a different lens (correctness, security, performance, operations, data, failure modes, user, maintenance, cost) and every pass must produce something the previous ones missed. Between two and eight passes, each ending in new falsifiable claims that can be added to the ISA. USE WHEN iterative depth, go deeper, multiple passes, review it again from another angle, what am I missing, blind spots, second pass, thorough review, harden this design, before a big merge. NOT FOR shifting the zoom level between tactical and strategic on one question (use aperture-oscillation), attacking a proposal adversarially (use red-team), or a single quick review where one read is enough.
argument-hint: "<artifact to review> [--passes N]"
---

# Iterative Depth

One reading of a design finds what that reading is good at finding. This skill rotates the lens on purpose.

## USE WHEN / NOT FOR

USE WHEN an artifact matters enough to read several times and one review has already found the obvious things.

NOT FOR shifting zoom between tactical and strategic on a single question, which is aperture-oscillation, or adversarial attack, which is red-team.

## What this produces

A stack of passes, each with its own findings and its own new claims.

## Done looks like

- Each pass names its lens up front and is scoped to that lens. A pass that drifts into every topic is one long pass with headings.
- Each pass produces at least one finding the earlier passes did not. A pass with nothing new is reported as exhausted, and that is the signal to stop.
- Every finding becomes a claim in ISA form, a falsifiable statement with the observation that would prove it unmet. Findings that cannot be written as claims are opinions and are marked as such.
- The pass count is chosen and stated, between two and eight, with a reason. Eight passes on a config change is ceremony; two on a payment path is negligence.
- A closing convergence section says which findings matter, which conflict with each other, and what order to fix them in.

## Output contract

```
## Target and pass plan
<what is under review> — <N> passes — <the lenses, in order, and why these>

## Pass 1 — <lens>
findings:
new claims:
  - [ ] <claim> — falsifier: <observation that disproves it>

## Pass 2 — <lens>
...

## Convergence
| finding | pass | severity | conflicts with | fix order |
|---|---|---|---|---|

## Exhaustion
<the lens where new findings stopped, and what that suggests>
```

## Lens catalog

Choose the lenses that fit the artifact. Order matters: correctness first, because a wrong thing does not need to be fast.

| lens | what it looks for |
|---|---|
| correctness | does it do the stated thing, at the boundaries and on the empty case |
| interface | is the contract clear to a caller who has not read the implementation |
| failure modes | partial writes, retries, timeouts, a dependency that answers slowly instead of failing |
| security | trust boundaries, input that crosses one, secrets in logs, who can call this |
| data | schema drift, nulls, duplicates, ordering, backfills, timezone handling |
| performance | the cost per call at real volume, the query plan, the N+1, the hot loop |
| operations | what a responder sees at 3am, what they can roll back, what alerts fire |
| maintenance | what the next person will misunderstand, what is duplicated, what has no test |
| cost | what this costs per month at projected volume, and what drives it |
| user | what the person on the other end experiences when it works and when it does not |

## Roles

Run passes at the **high** role and the convergence section at the **max** role, since reconciling conflicting findings is judgment. On a high-stakes artifact, assign at least one pass to the **cross** role from another vendor family, because shared-family blind spots survive any number of same-family passes.

## Constraints and gotchas

- Do not fix things mid-pass. Findings accumulate; edits come after convergence, or the later lenses are reviewing a moving target.
- Each lens reads the artifact again. A lens applied to the summary of pass 1 finds nothing new.
- Stop at exhaustion rather than the plan. Two productive passes beat six padded ones, and the write-up should say the plan was cut short.
- Conflicting findings are the most useful output. Performance and maintenance will disagree; name the tradeoff instead of resolving it silently.
- Keep every claim falsifiable. "Improve error handling" cannot be checked; "a timeout on the upstream call returns 504 and is logged with the request id" can.
