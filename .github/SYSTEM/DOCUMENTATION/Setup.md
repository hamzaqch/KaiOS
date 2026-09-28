---
version: 1.0.0
last_updated: 2026-09-28T00:00:00Z
convention: kaios-freshness-v1
---

# Setup

> First run, end to end. Five minutes to a working install, then an interview that teaches KaiOS what you work on. Everything beyond Python and PowerShell is optional, and the system is fully functional with none of it linked.

## The flow

```
  1. .github\scripts\Install.ps1   copy surfaces, create KAIOS_HOME, render absolute paths
  2. reopen VS Code       Copilot picks up the doctrine
  3. /kaios-setup         the interview → PROFILE.md, config.json
  4. optional links       MCP servers, Databricks CLI, API keys by env-var name
  5. project interview    → PROJECTS.md, per-project .instructions.md
  6. ISA seed             → <repo>/ISA.md for the first project
```

Steps 4 through 6 can be skipped and run later. Nothing downstream breaks if they are.

## 1 · Install.ps1

Run it from the cloned repository. Every script KaiOS ships lives in
`.github\scripts`, because the whole framework lives in `.github`. It needs no
administrator rights.

```powershell
.\.github\scripts\Install.ps1
```

What it does:

- creates `$env:KAIOS_HOME` (default `~/.kaios`) with the `CONFIG`, `USER`, `MEMORY` and `KAIOS` subtrees
- copies the doctrine tree from `.github/SYSTEM/` into `$KAIOS_HOME/SYSTEM/` so the installed copy is readable independent of the repository
- copies the Python package from `.github/kaios/` to `$KAIOS_HOME/lib/kaios/` so hooks can import it from any workspace
- copies agents, skills, hooks and instructions to the user-level Copilot directories under `~/.copilot/`
- renders absolute paths into the user-level hook registration, because a relative path in a user-level hook resolves against whatever directory the session opened in
- prints what it detected and what it skipped

It is **idempotent**. A second run changes nothing, and that is a tested claim rather than an intention: install twice into a temporary home and the trees are identical.

`.github\scripts\Init-Workspace.ps1 <path>` is the other half. Because the whole
framework is one directory, it is one copy: everything under `.github` lands in the
target repository's `.github`, and a `.vscode/mcp.json` is rendered from
`.github/SYSTEM/TEMPLATES/mcp.json.template`. The framework's own `scripts` and
`tests` stay behind — a work repository consumes KaiOS rather than building it —
and `-IncludeTests` carries the suite too. It **never overwrites a file that
already exists**: an existing `copilot-instructions.md` in a target repository is
that team's, and it stays theirs.

`.github\scripts\Uninstall.ps1` removes the installed surfaces and leaves `$KAIOS_HOME` alone, because that is where your memory lives.

## 2 · Detection

```
python -m kaios setup detect
```

Reports each tool as `found` or `missing`, with a version where one is available: Python, git, the GitHub CLI, the Databricks CLI, VS Code, the PowerShell version, and which MCP servers are already configured.

**It never fails because something is missing.** Missing is a finding, not an error. The output drives what the interview bothers to ask about — there is no point asking which Databricks profile to use on a machine with no Databricks CLI.

## 3 · The interview

```
/kaios-setup
```

The `kaios-setup` skill drives it and the `Setup` agent runs it. It asks a small number of questions, one at a time, and every one of them is skippable.

What it establishes for `USER/PROFILE.md`:

- your role and what you are responsible for
- the team, and who consumes your work
- the stack you actually work in, as opposed to the one on the job description
- how you want to be talked to — how much detail, how much pushback, whether to explain or just do it
- what "done" usually means in your environment: tests, review, a deployed artifact, a stakeholder sign-off

The interview writes what you said. It does not embellish, and it does not invent a persona. A profile with three honest lines is more useful than a page of guesses, and `PROFILE.md` is editable afterward by hand.

Your answers land in `USER/PROFILE.md`; tool choices and flags land in `CONFIG/config.json`.

## 4 · Optional links

Each one is asked about only if detection found the thing, and each is declined with a single word.

| Integration | What linking it does | Without it |
|---|---|---|
| MCP servers | renders `.vscode/mcp.json` from the template with the servers you chose | nothing is rendered; skills that would use one say so and fall back |
| Databricks CLI | records which profile to use in `config.json` | the `databricks` skill reports the CLI is absent and exits cleanly |
| API keys | records the **environment variable name** in `config.json` | features that need the key stay off |

**A key's value is never written to a file.** Only the name of the variable that holds it. Nothing in KaiOS reads a secret into the transcript, and `SecretsGuard` denies the attempt.

## 5 · The project interview

Then, one project at a time:

- what it is, in a sentence
- where it lives — path and remote
- how it is run, tested, and deployed
- what "ship it" means for this specific project, because it is different per repository and that difference is the thing worth writing down
- the aliases you actually use for it in conversation

Each project becomes a row in `USER/PROJECTS.md`:

```markdown
| Project | Path | Stack | Test | Deploy |
|---|---|---|---|---|
| ingest-pipeline | <workspace>/ingest | Python, Databricks | pytest | bundle deploy -t dev |
```

plus a routing alias table, so "the pipeline" resolves to one repository rather than a guess.

Where a project has rules of its own, the interview writes a scoped instructions file into that repository — `.github/instructions/<project>.instructions.md` with an `applyTo` glob — so the rule lives beside the code it governs instead of in a global file that every other project also loads.

## 6 · ISA seed

For the first project, setup offers to seed `<repo>/ISA.md`:

```
python -m kaios isa scaffold --project --slug <name> --goal "<what the project is for>"
```

The seed is a real ISA with a `## Goal` and the claims that can honestly be stated today — not a template full of placeholders. What is known but not yet probe-able goes into `## Not yet specified` as fog, which is the honest shape for a project nobody has fully specified yet.

From then on, the project ISA is that project's state of record. "Add a feature" means adding claims that do not hold yet.

## Verifying the install

```
python -m kaios doctor
```

One pass over paths, config, the hook registration, every hook module importing, the model registry, and the integrity checks. Every line is `PASS`, `WARN`, or `FAIL`; exit code is 0 when nothing failed. A `WARN` is almost always an optional integration that is not linked, which is a normal steady state.

The package lives at `.github/kaios`, so the import root is `.github`: run
`python -m kaios …` from the repository root with `PYTHONPATH=.github` set, or from
inside `.github`.

```
python -m kaios hooks probe
.github\scripts\Probe-Hooks.ps1
```

The first fires all eight events with sample input through Python. The second does the same through the PowerShell wrapper, which is the path a Windows session actually takes — so it is the one that catches a quoting or an encoding problem that the Python path never sees.

## Rendering from a fixture

The whole interview is reproducible without a human, which is what makes it testable:

```
python -m kaios setup render --answers .github/tests/fixtures/setup-answers.json
```

It writes the same profile, project table, scoped instructions, config and ISA seed that an interactive run would. That is how the setup path is verified in CI, on a machine with none of the optional tools installed.
