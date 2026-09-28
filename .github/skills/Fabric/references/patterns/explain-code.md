# Explain Code

> Explain what a piece of code does, why it is shaped that way, and what would break it.

## Done means
- The purpose is stated before the mechanism, in the caller's terms.
- The walkthrough follows the data, not the line order, and names the invariant each part maintains.
- Non-obvious choices are explained or explicitly marked as unexplained by the code.
- Failure behavior is described — what happens on bad input, on a dependency error, on a retry.
- The explanation is checkable against the code; no behavior is asserted that is not there.

## Output contract
```
## What it is for
## How it works
<prose following the data path, naming invariants>
## Interfaces
| in | out | side effects |
## Failure behavior
## Surprises
<the parts that would mislead a reader, and why they are that way>
## Questions the code cannot answer
```

## Gotchas
Do not narrate line by line; that is the code with extra words. Look for the invariant the code protects, because that is usually the real explanation. Say when a comment contradicts the code.
