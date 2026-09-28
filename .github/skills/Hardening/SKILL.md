---
name: hardening
description: "Makes a test suite find the bugs it is currently missing. Turns example-based tests into universally quantified properties, applies a mutation-testing mindset by asking which deliberate breakages the suite would let through, and ranks functions by branching complexity against test presence so effort lands where risk actually is. USE WHEN harden, hardening, strengthen the tests, test the tests, property test, property based testing, invariant, universally quantified, mutation testing, would the suite catch this, what bugs am I missing, my tests pass but it broke, flaky test, edge cases, fuzz the input, complexity hotspots, untested code, where is the risk, CRAP score. NOT FOR writing the first tests for a new feature (write them directly), grading model output quality (use evals), closing one claim on evidence (use verify), or security vulnerability hunting."
argument-hint: "[path or module to harden]"
---

# Hardening — test the tests

## What this produces

A suite that fails when the code is wrong. Concretely: a ranked list of where risk sits, a set of properties replacing brittle examples, and a list of mutations the current suite would have let through, each turned into a test or explicitly accepted.

## Done looks like

- Every hotspot above the chosen threshold is either covered or tombstoned with a reason.
- At least one test states a property that holds for all inputs in a range, not one input.
- For each function under hardening, a named mutation exists that the suite now catches and previously did not.
- The suite still passes, and the run that proves the new tests work is the run where they failed first against the unmodified code.

## USE WHEN

Tests pass and a defect shipped anyway, a module is about to be relied on by something new, coverage looks high and confidence is low, or someone asks what the suite is missing.

## NOT FOR

First tests for new code: write them, then come back. Grading prose or judgement output (`evals`). Closing a single claim (`verify`). Vulnerability research.

## Find the risk first

Coverage percentage is the wrong map. A trivial getter at 100 percent and a nine-branch parser at 60 percent average to something reassuring and meaningless. What matters is branching against testedness, which is what the hotspot score approximates.

Work down the ranked list, not across the file. The top five rows usually account for most of the real exposure, and hardening everything equally is how a hardening pass runs out of energy before it reaches the parser.

## From examples to properties

An example test says "for this input, this output". A property says "for any input in this set, this relation holds". The second finds bugs nobody thought of, which is the entire point.

Ask these of each function, and each yes is a property:

| Question | Property shape |
|---|---|
| Does it have an inverse? | round trip: `decode(encode(x)) == x` for all x |
| Is there a slower, obviously correct version? | oracle: `fast(x) == naive(x)` for all x |
| Does calling it twice change anything? | idempotence: `f(f(x)) == f(x)` |
| Does input order matter? | commutativity: `f(a, b) == f(b, a)` |
| Is something conserved? | invariant: row count, sum, set of keys preserved |
| Is there a total ordering? | monotonicity: larger input never yields smaller output |
| Should it ever raise? | totality: no input in the domain raises an unexpected type |

Then generate inputs deliberately rather than randomly-ish. The standard library's `random` with a fixed seed is enough; the value is in the *shape* of the inputs, not in the generator. Cover: empty, one element, two elements, the maximum you claim to support, duplicates, unicode outside the Latin range, negative and zero where a count is expected, and a value that is one past every documented boundary.

When a property fails, shrink before reporting. Cut the failing input in half repeatedly until it stops failing, then report the smallest input that still breaks. A twelve-element counterexample is a puzzle; a two-element one is a diagnosis.

## The mutation mindset

No mutation tool is installed here, and one is not needed to get most of the benefit. Do it by hand, as a thought experiment with a written answer.

Take a function and list the small wrong versions of it: flip a comparison operator, change a boundary from `<` to `<=`, swap two arguments, return early, drop the negation, replace a computed value with a constant, remove the exception handler. For each, ask whether any existing test would go red.

- A mutation nothing catches is a missing test, and the test to write is the one that catches exactly it.
- A mutation everything catches means the tests are duplicative there; that is information too.
- A mutation that changes behaviour nobody depends on is a signal the code has an unstated contract. Write the contract down, then decide whether it matters.

Do this on the top hotspots only. Done exhaustively it is busywork; done on the three functions that carry the branching, it is the highest-yield hour available.

## Tool contracts

<!-- keep: tool-contract -->

| Command | Contract |
|---|---|
| `python .github/skills/Hardening/hotspots.py <path> [<path> …]` | ranks functions by `complexity ** 2 + complexity` when no test names them, `complexity` when one does. `--tests DIR` adds a test tree to scan, `--limit N` sets rows printed, `--fail-over N` exits 1 when the top score exceeds N, `--include-private` scores single-underscore functions, `--json` emits the full report. Exit 0 clean, 1 a threshold was exceeded or a file failed to parse. |

The test-presence signal is a name-mention proxy, not real coverage. It over-credits a function whose name appears in an unrelated assertion and under-credits one exercised only indirectly. Treat the ranking as a place to look, never as a verdict.

## Constraints and gotchas

- A new test must be seen failing before it is trusted. Write it, run it against the unmodified code, watch it go red for the reason you expect, then make it pass. A test that was green from birth has proven nothing.
- Never weaken an assertion to make a flaky test pass. Find what is actually non-deterministic: time, ordering, a shared fixture, a real network call.
- Do not assert on incidental detail. A test that breaks when an unrelated log line changes will be deleted by the next person, and they will be right.
- Properties over examples, but keep two or three examples as documentation. A reader learns the function faster from one concrete case than from an invariant.
- Hardening is read-then-add. It does not license refactoring the code under test in the same pass; a changed implementation and a changed suite in one diff means neither one verified the other.
