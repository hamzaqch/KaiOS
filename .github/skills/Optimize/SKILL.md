---
name: optimize
description: "Improves one artifact against one measured number, with a baseline captured before the first change, a claim per iteration, and a stop rule written down in advance so the pass ends on purpose rather than on exhaustion. Applies to latency, cost, token count, accuracy, file size, build time or any target that can be read off a tool. USE WHEN optimize, make it faster, make it cheaper, reduce latency, cut the cost, shrink the token count, improve accuracy, tune this, better score, squeeze more out of, performance pass, it is too slow, too expensive, hill climb this number, iterate on this prompt, improve the prompt. NOT FOR repeating a check on a cadence (use loop), finding out whether something is correct at all (use verify or hardening), shrinking an oversized doctrine file (use trim), or a redesign where the metric is not yet known."
argument-hint: "<artifact> <target metric>"
---

# Optimize — one number, one stop rule

## What this produces

A measurably better artifact and a record of how it got there: a baseline, an iteration log where each step names what changed and what the number did, and a stop that was decided before the work started.

## Done looks like

- A baseline number exists, measured with the same command that will measure every iteration.
- The target is a number with a unit, and the stop rule is written down before the first change.
- Each iteration is one claim in the ISA, closed on a measurement rather than on a plausible-sounding change.
- The final measurement was taken on an unmodified checkout of the final state, not inferred from the last iteration's delta.
- Nothing else regressed: the correctness suite still passes, and that is stated with its evidence.

## USE WHEN

Something is too slow, too expensive, too large, or not accurate enough, and there is a command that can say how much.

## NOT FOR

Cadence work (`loop`). Correctness (`verify`, `hardening`). Shrinking an always-on file (`trim`). A redesign where the metric has not been chosen: choose it first, or the pass will optimize whatever is easiest to move.

## Before the first change

Three things, in this order, and skipping any of them makes the rest worthless.

**One metric.** Name it with a unit and a measurement command. "Faster" is not a metric; "p95 wall-clock seconds over the 50k fixture, from `python -m timeit`-style repeated runs" is. If two numbers matter, name the primary and write the second as a constraint that must not regress.

**A baseline.** Measure before touching anything, and measure it the way you intend to keep measuring. Run it at least three times and record the spread, because a change smaller than the spread is not a change. Most disappointing optimization passes are disappointing because the baseline was one lucky run.

**A stop rule.** Pick one and write it in the ISA:

| Stop rule | Stop when | Good for |
|---|---|---|
| Target reached | the number crosses a stated threshold | there is a real requirement |
| Diminishing returns | an iteration moves it less than N percent | there is no requirement, just "better" |
| Budget | N iterations, or a wall-clock box | the work is exploratory |
| Constraint hit | correctness, readability or cost would have to give | almost always the real stop |

Without this, the pass ends when someone gets bored, and the last change is usually the one that traded something valuable for two percent.

## The iteration

Each pass is one hypothesis, one change, one measurement. Bundling three changes to save time is how you learn that the number improved and not why.

- State the hypothesis first: what you believe is costing the number, and how much of it. Being wrong here is useful; being vague is not.
- Change one thing.
- Measure with the baseline command, same fixture, same repetitions.
- Record the delta in the ISA and close that iteration's claim on the measurement. A claim closed on "this should be faster" is not closed.
- Keep the change only if it earned its keep. A two percent gain that doubles the complexity of the hot path is a loss, and the honest move is to revert it and say so.

Measure where the cost actually is before the second iteration. One profile beats four guesses, and the usual finding is that the thing everyone suspected accounts for a small share of the total.

## Watch for the false win

Optimization is unusually good at producing numbers that improve while the system gets worse. The recurring shapes:

- **Measuring the cache.** The second run is fast because the first one warmed something. Clear it, or measure cold and warm separately and say which is which.
- **Shrinking the work.** The number improved because the code now does less: fewer rows, a skipped validation, an early return that swallows a case. Check the output is identical, not just the timing.
- **Moving the cost.** Latency left the function and arrived in the caller, or in a queue, or in someone else's dashboard. Measure the whole path.
- **Overfitting the fixture.** It is faster on the benchmark and unchanged in reality, because the fixture is not shaped like production data.
- **Trading correctness.** An accuracy pass that tightened a threshold and quietly raised the false-negative rate. The constraint metric exists to catch exactly this, so measure it every iteration, not at the end.

## Tool contracts

<!-- keep: tool-contract -->

| Command | Contract |
|---|---|
| `python -m kaios isa scaffold --slug optimize-<what> --goal "<metric> from <baseline> to <target>"` | the ISA that holds the iterations, one claim each |
| `python -m kaios isa frontier <path>` | the next iteration's claim |
| `python -m kaios memory capture --kind learning --text "…"` | what the profile actually showed, which is the durable part |

The measurement command is whatever the artifact needs, and it belongs in the ISA's Test Strategy so the next person measures the same thing. An optimization ISA whose measurement command is not written down cannot be resumed.

## Constraints and gotchas

- Never optimize something that is not yet correct. A fast wrong answer costs more to debug than a slow one.
- Report the spread alongside the number. A single figure implies a precision the measurement does not have.
- Take the final measurement fresh, from the final state, with nothing else running. Accumulated deltas drift.
- Keep the reverted attempts in the ISA's Decisions. The dead ends are what stop the next person spending a day on the same idea.
- State the cost of the win in the closing report: added complexity, a new dependency, a cache to invalidate, a subtlety a reader now has to know. A win reported without its cost will be undone by someone who only sees the cost.
