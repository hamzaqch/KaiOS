---
name: first-principles
description: Strip a problem down to what is physically or contractually true, sort every other element into soft constraint or assumption, then rebuild the solution from the fundamentals alone instead of from what the current design happens to do. Produces a constraint ledger and a from-scratch rebuild that is compared against the existing approach. USE WHEN first principles, from scratch, question the assumptions, is that actually a constraint, why do we do it this way, rethink this, the real limit, rebuild it, we inherited this design, everyone does it this way, challenge the premise. NOT FOR mapping feedback loops and structural behavior over time (use systems-thinking), tracing a specific failure to its cause (use root-cause-analysis), or generating many novel options (use be-creative).
argument-hint: "<the problem or existing design to rebuild>"
---

# First Principles

Most designs are inherited. This skill separates what is actually required from what is merely current.

## USE WHEN / NOT FOR

USE WHEN a design is inherited, a constraint is asserted without a source, or the third fix to the same area suggests the premise is wrong.

NOT FOR mapping feedback behavior over time, which is systems-thinking, or tracing a single failure, which is root-cause-analysis.

## What this produces

A constraint ledger and a rebuild.

## Done looks like

- Every element of the problem appears in the ledger, classified, with a reason for the classification.
- Every hard constraint names the source that makes it hard, a law of physics, a published API limit, a contract, a regulation, a budget someone signed. A constraint whose source is "we always have" is an assumption wearing a costume.
- At least one belief that the team currently treats as fixed has been reclassified as an assumption, or the ledger says explicitly that none could be, which is a real and reportable finding.
- The rebuild is described without reference to the existing implementation. If it is impossible to describe without saying "like the current system but", the rebuild has not happened yet.
- The rebuild is compared against the current approach on the dimensions that matter, and the recommendation is one of keep, adapt, or replace, with the cost of switching stated.

## Output contract

```
## Problem, restated
<what outcome is actually wanted, with no solution words in it>

## Constraint ledger
| element | class | source or reason | if this changed |
|---|---|---|---|

## Fundamentals
<the three to six irreducible truths the solution must respect>

## Rebuild from fundamentals
<the design that follows from the fundamentals alone>

## Comparison
| dimension | current | rebuild |
|---|---|---|

## Recommendation
keep | adapt | replace — <reason, and the cost of switching>
```

Classes for the ledger, exactly three.

| class | test that puts an element here |
|---|---|
| hard | violating it is impossible, illegal, or breaks a signed commitment. Physics, published limits, contracts, compliance. |
| soft | violating it costs money, time, goodwill, or effort. Real, but priced. Say the price. |
| assumption | nothing enforces it. It is habit, precedent, a copied pattern, or a guess nobody rechecked. |

The interesting work is almost always at the boundary between soft and assumption. Push every element down one class and see if anything actually stops you.

## Roles

Run this at the **max** role. Classification is judgment, and misclassifying an assumption as a hard constraint is exactly the failure this skill exists to prevent. A **cross** role pass on the finished ledger from a different vendor family catches inherited framing the first pass shared with the target.

## Constraints and gotchas

- Restate the problem in outcome terms before touching constraints. "We need a faster cache" is a solution; "reads must answer in under 50 ms at 2k per second" is a problem.
- Numbers beat adjectives. "Large dataset" hides the answer; "40 GB growing 2 GB a month" contains it.
- Verify the limits you call hard. Quota, rate limit, and size ceilings are published, and they are often not what the team remembers.
- A rebuild that lands on the current design is a good result, not a wasted pass. Say that the current design is justified and why, so nobody relitigates it next quarter.
- Do not use this on problems whose constraints are genuinely fixed and well understood. The ceremony costs more than it returns.
