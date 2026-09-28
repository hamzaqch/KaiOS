---
name: science
description: Run the scientific method as an engineering loop. State the goal as an observable outcome, write several competing falsifiable hypotheses, design the cheapest experiment that can distinguish them, measure honestly, then record a verdict that names which hypotheses died. Scales from a failing test to a performance mystery to validating that a shipped feature did what it promised. USE WHEN hypothesis, experiment, test this theory, how do we know, prove it, measure it, why is this slow, which change caused it, validate the feature, A vs B, I think it is X but I am not sure, debug something intermittent. NOT FOR structured multi-lens exploration of a design (use iterative-depth), incident forensics after an outage (use root-cause-analysis), or building the thing itself once the answer is known.
argument-hint: "<the question to settle> [--quick]"
---

# Science

Guessing and then changing code is not debugging. This skill makes the guess explicit, then kills it with evidence.

## USE WHEN / NOT FOR

USE WHEN you are about to change something on a hunch, a failure is intermittent, or a shipped feature's value is asserted rather than measured.

NOT FOR rotating analytical lenses over a design, which is iterative-depth, or forensics on a resolved incident, which is root-cause-analysis.

## What this produces

A verdict backed by a measurement someone else could repeat.

## Done looks like

- The goal is written as something observable, with a number or a state that can be checked. "Make it faster" is not a goal; "p95 under 200 ms on the same query set" is.
- At least two competing hypotheses exist, each falsifiable. One hypothesis is a hunch, not a method, and it biases every measurement that follows.
- Each hypothesis states the observation that would kill it, written before the experiment runs.
- The experiment distinguishes between hypotheses. If every hypothesis predicts the same result, the experiment is worthless and must be redesigned.
- The measurement is recorded as observed, including the inconvenient parts. Numbers that contradict the favored hypothesis are the most valuable output this skill produces.
- The verdict names which hypotheses survived, which died, and what the next experiment is if the question is still open.

## Output contract

```
## Goal
<observable outcome, with the number or state that defines success>

## Hypotheses
| id | hypothesis | predicts | killed by |
|---|---|---|---|

## Experiment
<what will be run, on what, how many times, what is held constant>
<the control, and why it is a fair one>

## Measurement
<raw observation — commands, outputs, numbers, timestamps>

## Verdict
survived: <ids>   died: <ids>   still open: <ids>
<what this licenses you to do next>
```

## Depths

| depth | shape | fits |
|---|---|---|
| quick | one hypothesis pair, one experiment, minutes | a failing test, an error nobody understands yet |
| standard | three or four hypotheses, a designed experiment with a control | a performance regression, a flaky job, a data mismatch |
| full | staged experiments where each result narrows the next | an intermittent production fault, a feature whose value is unproven |

In test-driven work the loop is the same one compressed: the failing test is the experiment, the hypothesis is the change you believe will pass it, and a test that passes before the change falsifies the hypothesis that the change was needed.

## Roles

Design hypotheses and read results at the **max** role, because experiment design is where bias enters. Run the experiment at the **high** role. When a result is surprising, get a **cross** role read from another vendor family before acting on it, since a satisfying explanation is the easiest thing in the world to accept.

## Constraints and gotchas

- Write the falsifier before you look. A falsifier chosen after the data arrives is a rationalization.
- Reproduce before explaining. An intermittent fault you cannot trigger on demand has not been understood, whatever the theory says.
- Change one thing. Two changes and one measurement produce a story, not a result.
- Do not measure on a warm cache, a loaded machine, or a different dataset than the one in question, and say which of those you controlled for.
- Absence of an error message is not evidence of success. Check the state that was supposed to change.
- Record the verdict where the work lives so the next person does not rerun the same experiment. Captures go through `python -m kaios memory capture`.
