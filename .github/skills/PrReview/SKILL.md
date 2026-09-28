---
name: pr-review
description: "Reviews a diff or a pull request for correctness bugs, silently swallowed failures, missing test coverage, and type design that lets bad states exist. Returns a severity table where every finding names the file, the line, what breaks, and the smallest fix. Runs at the max role in a fresh context, never as the author of the change. USE WHEN review this PR, review the diff, code review, look at my changes, check this patch, is this safe to merge, what did I miss, review before merge, silent failure, swallowed exception, error handling review, test coverage of this change, type design, does this need a test, second pair of eyes on the diff. NOT FOR writing the code (use algorithm), strengthening an existing suite (use hardening), grading model output (use evals), or reviewing prose."
argument-hint: "<patch file, PR number, or branch>"
---

# PrReview — read the diff like it will break

## What this produces

A severity table. One row per finding: severity, file and line, what goes wrong, and the smallest change that fixes it. Plus an explicit verdict on whether the change is safe to merge, and what would have to be true for it to be.

## Done looks like

- Every finding names a file and a line, and describes a failure a reader could trigger.
- Findings are ordered by severity, and the severity means what the table says it means.
- Missing test coverage is a finding when the change is behavioural, with the specific test named.
- The verdict is one of merge, merge after the listed fixes, or do not merge, with the reason.
- Nothing in the review is a style preference dressed as a defect.

## USE WHEN

A diff exists and someone has to decide whether it ships: a pull request, a local branch, a patch file, or work that just finished and is about to be committed.

## NOT FOR

Writing the code (`algorithm`). Hardening an existing suite (`hardening`). Grading model output (`evals`). Prose review.

## Who reviews

The **Reviewer** agent, at the max role, in a fresh context. Never the Builder, and never the context that wrote the change.

This is not ceremony. A context that produced the code has already decided the code is reasonable, and it will read the diff looking for confirmation. It also shares the exact blind spots that produced the defect. For a change touching auth, data deletion, money, or a surface other teams depend on, add the **Auditor** agent from a different vendor family: a same-family reviewer agrees with a same-family mistake far more often than chance.

Give the reviewer the diff, the ISA or the PR description, and nothing else. Do not give it the author's reasoning; if the change needs the reasoning to look correct, that is itself the finding.

## What to look for, in order

**Correctness under the inputs nobody sent.** Empty, one, many, maximum. Null where a value is assumed. Duplicates. Unicode outside the Latin range. Negative and zero where a count is expected. A value one past every boundary in the diff. Walk the new branches and ask which input reaches each one, and whether any input reaches none of them.

**Silent failure.** The highest-yield category and the hardest to see, because the code looks defensive. Every one of these is a finding unless the swallowing is deliberate and commented:

- An exception caught and turned into a default, a `None`, an empty list, or a log line with no re-raise.
- A fallback that produces a plausible wrong answer instead of stopping. A cache miss that returns empty, a lookup that defaults to the first row, a parse failure that yields zero.
- A return value nobody checks: an exit code, a boolean, a count of rows written.
- A retry that gives up quietly.
- A validation that logs and continues.

The test: if this code path fires in production at 3am, does anyone find out? If the answer is no, the severity is at least high, regardless of how unlikely the path looks.

**Test coverage of the change.** Not coverage percentage. For each behavioural change, name the test that would go red if the change were reverted. If there is no such test, that is a finding with the test named: what it asserts and which file it goes in. New error handling needs a test that triggers the error, which is the test people skip.

**Type design.** Does the change make a bad state representable? A pair of optional fields where exactly one must be set, a string that is really an enum, a dict passed through four layers, a boolean parameter that reverses the meaning of the call. Ask whether the invariant is enforced by the type or only by every caller remembering it.

**Concurrency and ordering.** Shared mutable state, a read-then-write without atomicity, an assumption that two things happen in the order they appear, a cache written before the thing it describes exists.

**What the diff removed.** Read the minus lines as carefully as the plus lines. A deleted guard, a dropped test, a removed validation, a narrowed retry: these are where regressions actually come from, and a reviewer reading only additions will miss every one.

## Severity

Use these definitions exactly, so the table means something.

| Severity | Definition |
|---|---|
| **critical** | data loss, a credential exposed, a destructive operation without a gate, or a wrong result presented as correct |
| **high** | a real failure path that is silent, or a defect reachable by an ordinary input |
| **medium** | a defect reachable by an unusual input, or missing coverage on behaviour that changed |
| **low** | a latent trap: works now, will mislead the next person |
| **note** | worth knowing, not worth blocking. Style goes here or nowhere |

Inflating severity to get attention destroys the table's usefulness within two reviews. If everything is high, nothing is.

## Output format contract

```
VERDICT: merge | merge after fixes | do not merge — <one line reason>

| # | Severity | Location | Finding | Fix |
|---|---|---|---|---|
| 1 | high | src/export.py:41 | write() failure is caught and discarded, so a failed run reports success | re-raise, or return the failure to the caller that alerts |

MISSING TESTS
- src/export.py:41 — a test where write() raises; assert the run exits non-zero.

WHAT I DID NOT CHECK
- The SQL against the real schema; no fixture database in the diff.
```

The last section is not optional. A review that does not say what it could not verify reads as a clean bill of health it has not earned.

## Tool contracts

<!-- keep: tool-contract -->

| Command | Contract |
|---|---|
| `python .github/skills/PrReview/diff_stats.py <patch>` | per-file churn and kind, whether any test file changed alongside source, and added lines matching known risk signals with a severity. `-` reads standard input, `--top N` limits rows, `--min-severity` filters, `--json` for machine output. Exit 0 no signals, 1 signals present. |

Produce the patch with the version control tool and pipe or save it. The signal list is a line-based hint, so it has both misses and false positives: a swallowed exception spread over two lines shows up only as a broad catch, and a legitimate `print` in a CLI is flagged. Read every signal, dismiss the ones that do not apply, and never treat an empty signal list as a clean review. The tool narrows where to look; it does not look.

## Constraints and gotchas

- Read the whole changed file, not only the hunk. Most real defects are an interaction between the new lines and something twenty lines away that the diff does not show.
- A finding without a location is not a finding. "Error handling could be better" wastes the author's time.
- Propose the smallest fix that closes the defect. A review that asks for a redesign will be argued with rather than acted on.
- Do not review the author. No "you forgot"; the code forgot.
- Review is read-only. Finding a defect does not license fixing it in the same pass: the whole value of the review is that it was independent of the change.
- When a finding is a guess, say so and say what would settle it. A confident wrong finding costs more than an honest uncertain one.
