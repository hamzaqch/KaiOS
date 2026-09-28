---
name: evals
description: "Turns a vague quality worry into a graded suite. Writes typed assertions per case, separates a capability suite from a regression suite, grades many samples per case so flakiness is visible, and reports pass@k and pass^k rather than one lucky output. Deterministic asserts are graded by a tool; rubric asserts need an explicit judge verdict and never pass by default. USE WHEN eval, evals, evaluate, benchmark, grade output, score the output, assertion, assert, rubric, judge, pass@k, pass^k, flaky output, is the prompt better, compare two prompts, compare agents, regression suite, did my change break the prompt, test a skill, test an agent, quality check, non-deterministic output. NOT FOR unit or property testing of code (use hardening), closing a single factual claim on evidence (use verify), or improving one artifact against a metric (use optimize)."
argument-hint: "[cases file] [outputs file]"
---

# Evals — assertion-first grading

## What this produces

Three files and a verdict. A `cases.jsonl` holding the inputs and what must be true of the answers, an `outputs.jsonl` holding what the model actually said across several samples, and a pass table naming which assert failed on which sample.

The split matters: the model under test produces the outputs, and a separate deterministic tool grades them. A grader that can be reasoned with is not a grader.

## Done looks like

- A `cases.jsonl` exists where every case names at least one assert that could fail.
- Each case is tagged `capability` or `regression`, and the regression cases each trace to a real defect that happened.
- Outputs hold at least three samples per case for anything whose failure mode is flakiness.
- `python .github/skills/Evals/eval_runner.py cases.jsonl outputs.jsonl` exits 0, or the failures are listed with the assert that caught them.
- No case passes because its rubric was never judged. Unjudged is a distinct, visible state.

## USE WHEN

The output is prose or a judgement rather than a value, one sample looked fine and you do not trust it, two prompts need comparing, or a change to an instruction file might have broken behaviour that nothing tests.

## NOT FOR

Code correctness (`hardening` for property and mutation thinking, the test suite for units). Closing one claim on one probe (`verify`). Hill-climbing a single artifact toward a number (`optimize`).

## Write the assert before the output

The discipline that makes this work: state what a good answer must contain before seeing any answer. Written afterwards, an assert describes the output you already got, and the suite becomes a mirror.

An assert is worth having only if a plausible bad answer would fail it. "Mentions invoices" fails nothing when the prompt is about invoices. "Names the failing step and does not speculate about the cause" fails plenty.

## Assert types

| Type | Passes when | Use for |
|---|---|---|
| `contains` | the substring is present | a required term, an identifier, a unit |
| `not_contains` | the substring is absent | leaked secrets, banned phrases, hedging |
| `regex` | the pattern matches | one of several acceptable words, a required shape |
| `not_regex` | the pattern does not match | a forbidden family of phrasings |
| `equals` | the whole output matches after trimming | a one-token classification |
| `json_path` | the dotted path exists, and equals `value` when given | structured output contracts |
| `llm-rubric` | a judge says so, recorded as a verdict | anything only a reader can assess |

Reach for a deterministic type first. Most rubrics that people write are two `contains` asserts and a `not_contains` wearing a costume. Keep the rubric for genuine judgement: tone, whether reasoning holds, whether an alert would actually help the person reading it.

A rubric assert is graded by a judge at the **max** role, in a fresh context, given the case input, the output, and the rubric text and nothing else. Its verdict is written to a judgements file and fed back to the runner. Until that happens the case reads UNJUDGED, which is a failure state, because a rubric that silently passes is worse than no rubric.

## Capability and regression

Two suites with different jobs, kept in the same file and separated by the `suite` field.

- **Capability**: can it do the thing at all. These get written when a feature is designed, they are allowed to fail for a while, and they are how you know a prompt change was an improvement.
- **Regression**: it broke once and must never break again. Every regression case traces to something that actually happened. These are never allowed to fail, and a red one blocks a change.

A suite where everything passes on the first run taught you nothing. Either the asserts are too loose or the cases are too easy; add the case that you expect to fail.

## pass@k and pass^k

Sampling is where evals earn their keep. One output tells you almost nothing about a non-deterministic system.

- **pass@k** — at least one of k samples passes. The right threshold when a human will review the output, or when retrying is free.
- **pass^k** — all k samples pass. The right threshold for anything unattended: a hook, a scheduled job, a safety gate, a refusal. A prod-deploy gate that holds four times out of five is broken.

Choose k for the cost of the failure, not for convenience. Three is a floor for anything worth measuring; use more for safety cases.

## Tool contracts

<!-- keep: tool-contract -->

| Command | Contract |
|---|---|
| `python .github/skills/Evals/eval_runner.py <cases.jsonl> <outputs.jsonl>` | grades deterministic asserts and prints a pass table. `--mode pass@k|pass^k` sets the default threshold, `--k N` the default sample count, `--suite S` grades one suite, `--rubrics FILE` supplies judge verdicts, `--json` emits the full report. Exit 0 all pass, 1 any failure or unjudged assert, 2 unreadable input. |

Record shapes:

```
cases.jsonl    {"id","suite","input","k","mode","asserts":[{"type","value","path"}]}
outputs.jsonl  {"id","sample","output"}
rubrics.jsonl  {"id","sample","assert_index","pass","reason"}
```

A worked case file: [references/cases-example.jsonl](references/cases-example.jsonl).

## Running a suite in Copilot

There is no batch runner here, and that is fine. Generate the outputs yourself: for each case, run the prompt under test k times, append one record per sample to `outputs.jsonl`, then grade once. Keep the generating context clean of the asserts — a model that has read the rubric will write to it, and the number stops meaning anything.

When comparing two prompts or two roles, hold the cases fixed and vary one thing. Two changes at once produces a number nobody can attribute.

## Constraints and gotchas

- Never let the model under test grade itself. Even with a perfect rubric it will find its own answer reasonable.
- Never show the asserts to the generating context. This is the single most common way a suite gets silently corrupted.
- A `contains` assert on a long phrase is brittle for no benefit. Assert the load-bearing token.
- Cases go in version control next to the thing they test. An eval suite that lives in someone's scratch directory is not a regression suite.
- When a case fails, read the output before touching the prompt. Half the time the assert is wrong, and fixing the prompt to satisfy a wrong assert makes the system worse.
- Do not put real credentials, customer data or internal identifiers in a case file. Cases are committed.
