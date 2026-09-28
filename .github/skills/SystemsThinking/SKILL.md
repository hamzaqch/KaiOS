---
name: systems-thinking
description: Structural analysis of a problem that keeps coming back. Works down the iceberg from events to patterns to structure to mental models, maps the reinforcing and balancing loops that generate the behavior, matches known archetypes like fixes that fail and shifting the burden, then ranks intervention points so effort goes where structure changes rather than where symptoms are loudest. USE WHEN systems thinking, feedback loop, causal loop, why does this keep happening, we fix it and it comes back, vicious cycle, leverage point, unintended consequence, second-order effect, the incentives are wrong, structural problem, iceberg. NOT FOR a single incident's causal chain (use root-cause-analysis), deconstructing a design to its constraints (use first-principles), or choosing between options (use council).
argument-hint: "<the recurring problem or system to map>"
---

# Systems Thinking

Behavior comes from structure. A problem that returns after every fix is being produced by something the fix did not touch.

## USE WHEN / NOT FOR

USE WHEN a problem returns after every fix, incentives appear to be producing the behavior, or a fix in one place keeps breaking another.

NOT FOR a single incident's causal chain, which is root-cause-analysis, or stripping a design to its constraints, which is first-principles.

## What this produces

A structural map and a ranked list of places to intervene.

## Done looks like

- The iceberg is worked all four levels down, from the visible event to the mental model that keeps the structure in place. Stopping at patterns is the common failure and it produces better dashboards, not fewer problems.
- At least one feedback loop is named, typed as reinforcing or balancing, and traced all the way around so the loop actually closes. An open chain is not a loop.
- Delays are marked on the loops. Most surprising system behavior is a delay somebody did not account for.
- Where an archetype fits, it is named, with the specific elements of this system filling its roles.
- Interventions are ranked by structural depth, not by ease, and the report is explicit about which cheap interventions will not hold.
- At least one place where current effort is being spent on a low-leverage intervention is identified, or the report says the current effort is already well placed.

## Output contract

```
## The recurring behavior
<what happens, how often, how long it has been happening>

## Iceberg
| level | what is here |
| events | <the visible incidents> |
| patterns | <the trend over time> |
| structure | <the rules, incentives, tooling, and flows that produce the trend> |
| mental models | <the beliefs that keep the structure unquestioned> |

## Loops
### L1 <name> — reinforcing | balancing
<A increases B increases C which feeds back into A> — delay at <where>
what would break this loop:

## Archetypes
| archetype | how it fits here | the usual escape |

## Leverage points, ranked
| # | intervention | depth | effort | holds? |

## Recommendation
<where to intervene, and what to stop spending effort on>
```

## Archetypes worth checking first

| archetype | signature | the escape |
|---|---|---|
| fixes that fail | the fix works, then the problem returns worse | address the structure the fix bypassed |
| shifting the burden | a workaround becomes the permanent path and the real capability atrophies | invest in the fundamental capability while the workaround still holds |
| limits to growth | a push that used to work stops working | find the balancing loop that is now dominant and relieve its constraint |
| success to the successful | the well-resourced area keeps getting resources | allocate on need or potential, not on current output |
| eroding goals | the target drifts down to meet actual performance | fix the standard to something external |
| tragedy of the commons | shared capacity degrades while each user behaves rationally | make the shared cost visible per user |
| escalation | each side responds to the other and both costs rise | change what is being compared |

## Depth of intervention

Deeper interventions are harder and hold longer. Rank by this order and say plainly where each candidate sits.

| depth | kind of intervention |
|---|---|
| shallowest | parameters, thresholds, more staff, more alerts |
| shallow | buffers and stocks |
| middle | flows, delays, the structure of the loops themselves |
| deep | information flows — who can see what, when |
| deeper | rules, incentives, defaults, constraints |
| deepest | goals, and the mental models that set them |

Parameter changes are where most effort goes and where the least change happens. Defaults and information flows are usually the cheapest deep intervention available to an engineering team.

## Roles

Run at the **max** role throughout. Loop identification is where this skill either earns its keep or produces a diagram nobody uses. A **cross** role review from another vendor family is useful on the mental-models level, because the analyst usually shares the team's beliefs.

## Constraints and gotchas

- Close every loop. If you cannot trace the last arrow back to the first element, you have a causal chain, and root-cause-analysis is the right skill for it.
- Name delays explicitly with rough durations. "Hiring helps in two quarters" behaves nothing like "hiring helps next week".
- Do not force an archetype. A wrong archetype makes a system look understood when it is not.
- A diagram is not a recommendation. End with the intervention, the depth, and what to stop doing.
- Beware of solving the loop you can see. The dominant loop often sits in another team's system, and saying so is a legitimate finding.
