# Refactor Plan

> Plan a behavior-preserving restructuring that can be merged in pieces without a long-lived branch.

## Done means
- The current problem is stated as a cost someone pays, not as an aesthetic complaint.
- The target shape is described concretely enough that two engineers would build the same thing.
- The plan is a sequence of steps each of which leaves the tests green and is independently mergeable.
- The safety net exists first — the tests that prove behavior is unchanged are named or written before the move.
- Anything that changes behavior is called out and separated from the refactor.
- A stopping point is defined, so a half-done refactor is a valid end state rather than a mess.

## Output contract
```
## Cost of the current shape
<the concrete cost — bug class, onboarding time, change amplification>
## Target shape
## Safety net
<tests that must exist and pass before step 1>
## Steps
| # | step | mergeable alone? | tests that prove it |
## Behavior changes (should be none)
## Stop-early point
```

## Gotchas
A refactor that changes behavior is a rewrite and needs different review. Never combine a move with an edit in one commit; the diff becomes unreviewable. If the safety net cannot be built, say so — that is a reason not to refactor yet.
