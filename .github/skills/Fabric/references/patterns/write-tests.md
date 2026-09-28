# Write Tests

> Produce tests that would fail if the behavior regressed, and that say what broke when they do.

## Done means
- Each test asserts one behavior and its name states that behavior.
- The happy path, the empty case, the boundary, and at least one error path are covered.
- Assertions check the state or value that matters, not merely that nothing raised.
- Tests are deterministic — no reliance on wall clock, network, ordering, or leftover state.
- Failure output identifies the cause without a debugger.
- Every test would actually fail if the behavior under test were removed. Say which ones you verified that way.

## Output contract
The test code, ready to run, in the project's existing framework and style, then a coverage note as a table of behavior against the test that covers it, then a list of behaviors deliberately left untested with the reason.

## Gotchas
A test that passes against a broken implementation is worse than no test. Prefer real objects to mocks where cheap; a mock asserts your belief about a dependency, not the dependency. Do not test the language or the framework.
