# Draft PR Description

> Write the description a reviewer needs in order to review well, in the order they need it.

## Done means
- The first paragraph says what changes for a user or caller, not which files moved.
- The reason for the change is stated, with a link or reference to the issue or incident behind it.
- The review guide points at the two or three places where judgment is actually needed.
- Verification is evidence, not intent — the commands run and what they printed.
- Risk, rollback, and anything deliberately left out are stated.
- The description is derived from the actual diff, not from the intent the author started with.

## Output contract
```
## What changes
## Why
## How to review
<the files or hunks that carry the risk, and the question to ask about each>
## Verification
<commands run, and their result>
## Risk and rollback
## Out of scope
```

## Gotchas
Do not list every file; the diff already does that. Say when a change is mechanical so the reviewer can skim it. If the change does two unrelated things, say so in the description and offer to split it.
