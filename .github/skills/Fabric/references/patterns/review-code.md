# Review Code

> Find the defects that matter in a diff or a file, each with a location, a mechanism, and a fix.

## Done means
- Every finding names file and line, and describes the input or condition that triggers the problem.
- Findings are ordered by consequence, correctness before style, and style findings are marked as such.
- Each finding has a fix specific enough to apply, or a reason the right fix is a design decision.
- Error paths, empty inputs, and boundary values were checked explicitly, and the review says so.
- Things the change does well are noted in one line, so the author knows what not to undo.

## Output contract
```
## Verdict
approve | approve with comments | request changes — <one sentence>

## Findings
| # | location | severity | finding | fix |

## Tests
<what is untested that should be, and the case that would catch each finding>

## Good
<one or two lines>
```

Severity is one of critical, high, medium, low. Critical means data loss, a security hole, or a correctness bug on the main path.

## Gotchas
Read the surrounding code, not just the diff; a correct-looking change can break an invariant held elsewhere. Do not restyle code the change did not touch. Concurrency, retries, and partial failure are where real defects hide.
