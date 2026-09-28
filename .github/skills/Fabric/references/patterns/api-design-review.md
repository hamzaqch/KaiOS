# API Design Review

> Review an interface the way its callers will meet it, before it is expensive to change.

## Done means
- The review is written from a caller's position, including a caller who has not read the implementation.
- Naming, types, and defaults are checked for whether the wrong call is easy to write.
- Error behavior is specified — what the caller gets, whether it is retryable, whether partial success is possible.
- Versioning and compatibility are addressed, including what happens to existing callers.
- Every finding says whether it is cheap to fix now and expensive later, which is the whole reason for the review.

## Output contract
```
## Interface under review
## Caller walkthrough
<the two or three most common calls, written out as a caller would write them>
## Findings
| # | finding | caller impact | cheap now / expensive later | fix |
## Error contract
| condition | what the caller sees | retryable? |
## Compatibility
## Verdict
```

## Gotchas
Optional parameters with defaults are where correctness goes to die; check what happens when the caller omits one. Booleans in a signature almost always want an enum. An endpoint that can partially succeed must say so in its response, not in its documentation.
