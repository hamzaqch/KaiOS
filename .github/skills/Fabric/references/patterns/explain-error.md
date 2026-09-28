# Explain Error

> Turn an error message or stack trace into a cause, a check, and a fix.

## Done means
- The actual failing operation is identified, distinguished from the frame where the error surfaced.
- The message is translated into what the code was trying to do when it failed.
- At least two candidate causes are given when the message is ambiguous, each with the observation that distinguishes them.
- A concrete next command or check is given, one that will discriminate between the candidates.
- The fix addresses the cause; where only a workaround exists, it is labelled a workaround.

## Output contract
```
## What failed
## What the message means
## Likely causes
| # | cause | how to tell |
## Next check
<the exact command or observation>
## Fix
## Why it happened here
```

## Gotchas
The deepest frame is usually not the interesting one; find the last frame in the project's own code. A wrapped exception hides the real cause, so read the whole chain. Do not offer five fixes; offer the discriminating check first.
