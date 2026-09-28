---
name: python
description: Rules for every Python file in this repository — standard library only, typed, argparse CLIs, subprocess argument arrays.
applyTo: "**/*.py"
version: 1.0.0
last_updated: 2026-09-28T00:00:00Z
convention: kaios-freshness-v1
---

# Python

## Standard library only

No third-party imports anywhere. The package index may not be reachable from a work machine, so a dependency is a thing that stops the install rather than a thing that speeds up the code. Python 3.10 is the floor.

When a task feels like it needs a library: `json`, `pathlib`, `argparse`, `subprocess`, `dataclasses`, `re`, `datetime`, `urllib.request`, `sqlite3`, `csv`, `hashlib`, `tomllib`, `unittest` and `typing` cover almost all of it. If none of them do, that is a design conversation, not an import.

`python -m kaios integrity imports` fails the build on a non-standard-library import.

## Shape

- Type hints on every function signature, including the return. `-> None` is a hint.
- `dataclasses` for structured data. A dict with five known keys is a dataclass that has not been written yet.
- `pathlib.Path` for paths. Never string concatenation, never `os.path.join` in new code.
- Module-level docstring saying what the module owns, in a sentence.
- Functions do one thing and return a value. A function that both computes and prints is two functions.
- Explicit is better than clever. A reader six months from now is the audience.

## CLIs

`argparse`, subcommands as subparsers, and every CLI responds to `--help` with exit code 0. JSON on stdout by default so output is machine-readable; `--md` when a human-facing form is wanted.

Exit codes are uniform across every entry point in this repository:

| Code | Means |
|---|---|
| 0 | success |
| 1 | the thing being checked failed, or the operation failed |
| 2 | usage error — bad arguments, missing required input |

Errors go to stderr with a message that says what to do about it. A traceback reaching a user is a bug in the error handling.

## Subprocess

**Always an argument array. Never a shell string.**

```python
subprocess.run(["git", "log", "--oneline", "--", str(path)], capture_output=True, text=True, check=False)
```

Never `shell=True`, and never an f-string built from anything that came from outside the function. That is the whole rule and it has no exceptions in this repository. A path with a space, a branch name with a semicolon, or a filename someone else chose is enough to turn a shell string into an injection.

Always pass `check=False` and inspect `returncode` yourself, or pass `check=True` deliberately because a raise is the behaviour you want. Never ignore the return code — a command that failed silently is worse than one that crashed.

Set `timeout=` on anything that talks to a network or another machine.

## Errors and failure

Catch the exception you can do something about. A bare `except:` or `except Exception:` that swallows and continues hides the failure that mattered.

When a fallback is legitimate, log the reason the primary path failed before taking it. A silent fallback is how a system spends six weeks running in degraded mode with nobody noticing.

Never return a sentinel that looks like success. If a function cannot do its job, raise or return an explicit failure the caller has to handle.

## Hook modules specifically

- One rule per module. The module docstring states the rule in one sentence.
- Every field read from the event dict uses `.get(...)` — every field is optional, always.
- Return `None` when there is nothing to say. That is the common case.
- Never raise on purpose. The runner catches, but a module that raises is a rule that did not fire.
- Never write to the ISA. Hooks read; the model writes.

## Tests

Every module has a test. Every hook module has a test that proves its rule fires and a test that proves it stays quiet when it should. See `.github/tests/**`.
