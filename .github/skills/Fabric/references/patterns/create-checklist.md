# Create Checklist

> Turn a procedure or a set of requirements into a checklist someone under time pressure can actually follow.

## Done means
- Every item is observable. The reader can tell whether it is done without interpretation.
- Items are ordered by dependency, and anything order-sensitive says why.
- Each item is one action with one subject. Compound items hide skipped work.
- Items that are gates, where proceeding without them causes damage, are marked as gates.
- The list is short enough to be used. Over about twenty items it needs splitting into phases.

## Output contract
```
## Before you start
| # | check | gate? | how you know it is done |
## During
## After
## If something fails
<the rollback or escalation, in one or two lines>
```

## Gotchas
A checklist is not documentation; it assumes the reader knows the domain and only needs to not forget. Do not include steps that cannot be skipped by accident. Write "confirm X is Y", not "check X".
