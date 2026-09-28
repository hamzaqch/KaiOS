# Write ADR

> Record an architecture decision so that a year from now someone can tell whether the reasoning still holds.

## Done means
- The decision is stated in one sentence in the present tense.
- The context describes the forces at the time, including constraints that will not be obvious later.
- Options considered and rejected appear with the reason each was rejected. An ADR with one option documents nothing.
- Consequences include the bad ones the team accepted knowingly.
- The record says what would make this decision worth revisiting.

## Output contract
```
# ADR-<n> — <decision in one line>
status: proposed | accepted | superseded by ADR-<n>
date: <iso>

## Context
## Decision
## Options considered
| option | why not |
## Consequences
positive:
negative accepted:
## Revisit when
```

## Gotchas
Write it at the time of the decision; reconstructed ADRs launder the reasoning. Never edit an accepted ADR to match a later change; supersede it. Name the constraint that drove the choice even when it is embarrassing, such as a deadline or a missing skill on the team.
