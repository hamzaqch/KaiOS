---
name: aperture-oscillation
description: Hold one question fixed and deliberately change the zoom on it. A narrow pass answers it at the level of this file, this call, this week. A wide pass answers the same question at the level of the system, the team, the year. A synthesis pass names where the two answers disagree, because the disagreement is where scope is wrong. Ends in a scope recommendation. USE WHEN aperture, zoom out, zoom in, bigger picture, are we solving the right problem, tactical vs strategic, is this the right scope, local fix or real fix, scope creep, we keep patching this, should this be a bigger change. NOT FOR rotating analytical lenses over the same scope (use iterative-depth), mapping feedback structure (use systems-thinking), or deciding between named options (use council).
argument-hint: "<the question to oscillate>"
---

# Aperture Oscillation

The same question has different answers at different zoom levels. When those answers disagree, the scope is the actual problem.

## USE WHEN / NOT FOR

USE WHEN you suspect you are solving the wrong-sized problem, or two people are both right because they are arguing at different zoom levels.

NOT FOR rotating lenses at one fixed scope, which is iterative-depth, or choosing among named options, which is council.

## What this produces

Three passes on one unchanged question, and a scope call.

## Done looks like

- The question is written once and never rewritten between passes. Changing the question is what makes this ceremony rather than analysis.
- The narrow pass answers within the immediate boundary and names that boundary explicitly.
- The wide pass answers at system, team, and time-horizon scale, and is allowed to say the narrow answer is beside the point.
- The synthesis names every tension between the two answers, in the form "narrow says X, wide says Y, they disagree because Z".
- A scope recommendation is stated as one of act narrow, act wide, act narrow now and wide later with the trigger for later, or the scope is wrong and here is the right one.
- Anything the oscillation revealed that neither pass would have found alone is called out. That is the reason the skill exists.

## Output contract

```
## Question
<one sentence, held constant>

## Narrow aperture
boundary: <this file / this endpoint / this sprint>
answer:
what this aperture cannot see:

## Wide aperture
boundary: <this service / this team / the next two years>
answer:
what this aperture cannot see:

## Synthesis
| tension | narrow says | wide says | why they disagree |
|---|---|---|---|

## Scope recommendation
act narrow | act wide | narrow now, wide at <trigger> | the scope itself is wrong — <the right one>

## Coherence
<does the narrow action move toward the wide answer or away from it>
```

The coherence line is the payoff. A narrow fix that moves away from the wide answer is technical debt taken on knowingly, which is fine, as long as it is written down as that.

## When each aperture wins

| situation | aperture |
|---|---|
| a bug with a bounded cause and a shipping deadline | narrow |
| the third fix to the same area this quarter | wide, the pattern is the problem |
| a design that is locally elegant and globally duplicated | wide |
| a migration proposal that nobody can cost | narrow first, to find the real unit cost |
| an argument where two people are both right | the apertures differ, name them |

## Roles

Both passes and the synthesis run at the **max** role. This is scope judgment, which is the most expensive thing to get wrong and the cheapest thing to get a second opinion on. A **cross** role read of the synthesis from a different vendor family is worth it before a scope decision that commits a quarter.

## Constraints and gotchas

- Two apertures, not five. Adding a middle pass produces averaging, and the tension disappears exactly where it was useful.
- The wide pass is not permission to redesign everything. It answers the same question; it does not substitute a more interesting one.
- Write what each aperture cannot see. That admission is what makes the synthesis honest.
- If both passes agree completely, say so and stop. Agreement across apertures is a strong signal that the scope is right, and it is a short report.
- Do not use this to stall. The output is a recommendation with a scope attached, not a standing invitation to keep thinking.
