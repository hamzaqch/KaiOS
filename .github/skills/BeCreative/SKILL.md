---
name: be-creative
description: Divergent ideation using verbalized sampling. Instead of one confident answer, generate several genuinely different candidates in the same pass, each with an explicit probability of being the obvious response, then argue for the strongest rather than the most likely. A second mode expands a seed set into a diverse corpus for tests, fixtures, or evaluation cases. USE WHEN be creative, brainstorm, give me options, think differently, unusual approach, name this, generate variations, I need alternatives, the obvious answer is boring, unstick me, come up with test cases, expand this into examples, synthetic examples, diverse fixtures. NOT FOR choosing between options that already exist (use compare-options or council), attacking a plan (use red-team), or any task where one correct answer exists.
argument-hint: "<the thing to generate ideas for> [--n 5] [--expand]"
---

# Be Creative

Asked for an idea, a model returns the centre of its distribution. Asking for several with stated probabilities pulls the tails into view.

## USE WHEN / NOT FOR

USE WHEN the first answer is obvious and probably not the best one, or you need a diverse set of examples rather than one good one.

NOT FOR choosing among options that already exist, which is compare-options or council, or any task with a single correct answer.

## What this produces

A candidate set that is diverse by construction, and a defended pick.

## Done looks like

- The requested number of candidates exist, defaulting to five, each with a probability estimate of how likely it is to be the first thing a model would say.
- The candidates differ in kind, not in wording. Five phrasings of one idea is one candidate.
- At least one candidate sits below a 0.10 probability, or the output says explicitly that the space is genuinely narrow, which is a real finding.
- Each candidate names the mechanism that makes it work, so an idea can be evaluated rather than admired.
- The pick is argued on merit against stated criteria, and the pick is allowed to be a low-probability candidate. Choosing the highest-probability candidate every time means the sampling did nothing.
- Discarded candidates stay in the output with one line on why they lost. They are the raw material for the next pass.

## Verbalized sampling

Ask for the distribution, not the mode. Each candidate carries a number for how typical it is, and low numbers are the interesting ones. Diversity is enforced along an axis the request names — mechanism, register, audience, time horizon, constraint relaxed — and the axis is stated so a reader can tell the candidates apart on purpose rather than by accident.

Push at least one candidate through each of these moves, since they reliably produce different shapes.

| move | what it does |
|---|---|
| invert | do the opposite of the obvious thing and see what it buys |
| relax a constraint | pick the constraint everyone assumes and drop it |
| steal from elsewhere | apply a solved pattern from an unrelated field |
| scale extremes | solve it for a hundred times more, or for exactly one |
| remove the thing | solve the problem by deleting the component that has it |

## Output contract

```
## Brief
<what is wanted, and the criteria the winner has to satisfy>
axis of diversity: <mechanism | register | audience | horizon | constraint>

## Candidates
| # | candidate | p(obvious) | mechanism | strongest objection |

## Pick
<the candidate>, because <argument against the criteria, not against the probabilities>

## Runners-up
<one line each on why they lost and what would make them win>
```

## Corpus expansion mode

Given a handful of seed examples, produce a larger set that covers the space rather than repeating the seeds. Done means the output varies along the dimensions that matter to the consumer — length, register, difficulty, malformedness, edge cases, adversarial inputs — the dimensions are named in a table, coverage per dimension is stated, and near-duplicates of the seeds are removed rather than counted. Label anything synthetic as synthetic; a fixture mistaken for real data is a future incident.

## Roles

Run at the **max** role. Diversity is the whole product, and lower-rung models collapse toward the mode, which is precisely the failure this skill exists to avoid. For a wider spread on something expensive, run the same brief at the **cross** and **third** roles and merge the candidate sets. Different vendor families have different modes, so their tails differ, and that is free diversity.

## Constraints and gotchas

- Generate before judging. Evaluating candidate one before writing candidate five is how the set collapses.
- Probabilities are self-reported estimates, not measurements. They are there to force spread, and they should not be presented as calibrated.
- Novelty is not the goal; a novel idea that fails the criteria is a worse answer than an obvious one that works. Say so when the obvious candidate wins.
- Check whether something already does this before presenting an idea as new, especially for tooling.
- Do not generate candidates that violate a hard constraint and then present them as bold. Note the constraint and relax it deliberately, or leave it alone.
