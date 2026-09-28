---
name: tests
description: Rules for the test suite — a test exists to fail on a real defect, runs with no network and no installed extras, and is named after the claim it closes.
applyTo: "**/tests/**"
version: 1.0.0
last_updated: 2026-09-28T00:00:00Z
convention: kaios-freshness-v1
---

# Tests

## What a test is for

A test exists to fail when something is actually wrong. A test that passes no matter what the code does is worse than no test: it costs the same to run and it buys false confidence.

Before writing a test, know what change to the code would make it fail. If nothing would, the test is asserting on the wrong thing.

## Running

`python -m pytest tests -q`, and the suite must also run under `python -m unittest` because pytest may not be installed on a work machine. That means: `unittest.TestCase` classes or plain `test_*` functions with bare `assert`, never a pytest fixture, never a decorator from a plugin, never `pytest.mark`.

The suite runs with **no network, no installed extras, and no optional tool present**. A test that needs a CLI, a workspace, or an endpoint is either rewritten against a fixture or it asserts the clean-failure path — that the code reports the tool is absent and exits cleanly. Both are useful; a skip is usually neither.

## Naming

`.github/tests/test_<module>.py` for this framework, or the work repository's own tests directory, and each test function named after the claim it closes rather than the function it calls. `test_reject_row_lands_in_reject_table`, not `test_ingest_2`. When a test closes a claim from an ISA, the claim identifier goes in the docstring so the evidence stub can point at the test by name.

## Shape

- One behaviour per test. A test asserting six things tells you one of six broke.
- Arrange, act, assert, with the assert saying what was expected in its message.
- `tempfile.TemporaryDirectory()` for anything touching disk. No test writes outside its own temporary directory, and no test depends on another test's leftovers.
- Fixtures as real files under `.github/tests/fixtures/`, not as string literals buried in the test. A fixture you can open in an editor is a fixture you can debug.
- No sleeps. If a test needs to wait for something, it is testing the wrong seam.
- Deterministic. No real clock, no random seed left unset, no ordering dependence between tests.

## Table-driven where the input is a set

When a rule has many cases — a guard that must deny five command shapes and stay quiet on three others — write one table and one loop over it, with the case in the assertion message. Adding the sixth case then costs one row, which is what makes the table get extended instead of ignored.

```python
CASES = [
    ("rm -rf /", "deny"),
    ("git status", None),
]
for command, expected in CASES:
    with self.subTest(command=command):
        ...
```

## What the suite must cover

- **Containment.** Every term in `.github/tests/containment.txt` greps to zero hits across the repository. One hit fails the build.
- **Imports.** No module imports outside the standard library.
- **Hooks.** Every module: its rule fires on the case it exists for, it stays quiet otherwise, and a module that raises still yields valid JSON with the session continuing.
- **Skills and agents.** Frontmatter schema, and for agents that the generated model list matches what the registry resolves.
- **The ISA format.** A malformed ISA fails `isa check` for each hard failure listed in the format spec. This is the important one: a checker that passes bad input is worse than no checker.
- **PowerShell.** Every `.ps1` parses under 5.1 rules with newer-only tokens banned.

## Claims about the suite

"The tests pass" closes on the actual output of the actual run, pasted or quoted. Not on the suite having passed earlier, not on the change looking safe. Re-run after the last edit, every time.
