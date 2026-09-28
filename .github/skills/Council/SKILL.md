---
name: council
description: Multi-model debate on a decision with a visible transcript. Seats one member per vendor family available in the model registry, briefs each on the question, and runs a 3-round DEBATE (opening positions, rebuttals, closing) or a 1-round QUICK check, ending in a verdict plus recorded dissent. Use it when a choice is consequential, reversible only at cost, and reasonable engineers would disagree. USE WHEN council, convene a council, debate this, get multiple perspectives, weigh the options, second opinion, second look, what would other models say, which approach should we take, deliberate, adjudicate a disagreement, decide between two designs. NOT FOR one-sided attack on a proposal (use red-team), questions with a single verifiable answer where a tool settles it, or trivial choices where the cost of deliberating exceeds the cost of being wrong.
argument-hint: "<the decision or question> [--quick]"
---

# Council

Put a real disagreement in front of several models from different vendor families and make them argue where you can see it.

## USE WHEN / NOT FOR

USE WHEN a consequential choice is genuinely contested, more than one option survives scrutiny, and you want different vendor families arguing where you can see it.

NOT FOR one-sided attack on a proposal, which is red-team, or questions a tool or a measurement settles. A council cannot vote a fact into being true.

## What this produces

A transcript readers can audit, ending in a decision they can act on.

## Done looks like

- The question is stated once, as a decision with named options, before any member speaks. A council on an unstated question produces essays.
- Each seat is a different vendor family drawn from the registry. Two seats from one family is one opinion with extra steps.
- Every member's contribution is visible in the transcript, attributed to its seat by role, never to a model name.
- Members actually engage. A round where nobody changes, concedes, or sharpens anything is a failed round, and the write-up says so.
- The verdict names the chosen option, the decisive reason, and what would change the answer.
- Dissent is recorded even when it lost, with the condition under which the dissenter would be right.

## Modes

| mode | rounds | when to use |
|---|---|---|
| DEBATE | 3 | architecture, a migration, a hiring-shaped tradeoff, anything hard to reverse |
| QUICK | 1 | a second look before shipping, a sanity check on a plan, choosing between two close options |

DEBATE rounds are opening positions, then rebuttals where each member attacks the others' strongest point, then closings where each member states their final position and what moved them. QUICK is one round of independent positions plus a synthesis.

## Roles, seating, and the second-look rule

Seats come from the role registry, one per vendor family present in it. The **max** role chairs and writes the synthesis. The **cross** role fills the second seat and the **third** role the third, because they resolve to different families by construction. The **research** role joins as a non-voting seat when the question turns on external facts, and its job is to bring sources, not opinions.

**A second look is always a different vendor family from the builder.** A model reviewing work from its own family shares that family's blind spots and will confidently agree with them. When the artifact under debate was produced at the **high** role by one family, the reviewing seat comes from another. This rule is not advisory; a council that breaks it has not held a review.

The Kai orchestrator and the Council-facing agents carry the dispatch. Reference seats by role in all output.

## Output contract

```
## Question
<the decision, the options, what is at stake>

## Round 1 — opening positions
### Seat (max)
### Seat (cross)
### Seat (third)

## Round 2 — rebuttals        (DEBATE only)
## Round 3 — closings         (DEBATE only)

## Verdict
<chosen option> — <the decisive reason in two sentences>

## Dissent
<who disagreed, what they would need to see to be proven right>

## What would change this
<the observation or measurement that flips the verdict>
```

Keep each member's turn to a few short paragraphs. Length is not persuasion.

## Constraints and gotchas

- Brief every seat on the same material. A member arguing from different facts is noise, not a perspective.
- Do not let members converge early to be agreeable. If two seats agree in round 1, the chair assigns one of them the strongest opposing case for round 2.
- The chair does not vote its own prior. Its job is to weigh what was said, including against its own opening.
- A council cannot settle a factual question. When the disagreement is about a fact, stop and measure it instead. Say so plainly.
- Name no models in any output. Roles only.
- Record the verdict where the decision lives, an ISA decision line or an architecture note, or the council was theater.
