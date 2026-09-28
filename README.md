# KaiOS

KaiOS is a work-only operating system for GitHub Copilot in VS Code. Copilot out of the box is a very good autocomplete with a chat window; it has no doctrine, no written definition of done, no gate that stops it from claiming success it cannot prove, no memory between sessions, and no strategy for the several vendors' models it can reach. KaiOS supplies all of that as plain files that Copilot already knows how to discover — a constitution, path-scoped instructions, role-pinned agents, skills, and hooks that run on every chat event.

The shape of the thing is one loop. Work starts by writing down what done means as falsifiable claims, in a file called an ISA. The Algorithm climbs those claims. Hooks enforce the rules that should never depend on anyone remembering them, including a guard that refuses destructive commands and a gate that will not let a session end with a claim marked done and no evidence attached. Agents carry roles rather than personalities, each pinned to a model rung, and the seat that reviews work is never the seat that built it. Everything it learns lands somewhere structural instead of in a chat log. It installs with one PowerShell script, needs nothing beyond what a locked-down work machine already has, and contains no personal content of any kind.

## Requirements

| Need | Why |
|---|---|
| Windows | The installer and the hook wrapper are PowerShell. |
| VS Code with GitHub Copilot | KaiOS is a set of files Copilot discovers. |
| Python 3.10 or newer | Hook logic and every command-line tool. Standard library only. |
| Windows PowerShell 5.1 | Already on every supported Windows build. |

Nothing else. No Node, no package manager, no compiled binaries, no third-party Python packages, no admin rights. Everything beyond this table is optional.

## Five-minute install

Clone the repository, then run the installer from its root.

```
git clone <your-fork-url> KaiOS
cd KaiOS
powershell -ExecutionPolicy Bypass -File Install.ps1
```

The installer copies the agents, skills and instructions into your user-level Copilot directory, creates the KaiOS home tree, installs the doctrine copy, renders the hook registry with absolute paths, and sets `KAIOS_HOME` if it is not already set. It compares file contents before writing, so running it twice reports `0 files changed`.

Open VS Code and confirm hooks are enabled. In Settings, `chat.useHooks` must be on; hooks are ignored entirely while it is off, with no error to tell you so. Then open a new Copilot chat — the first response should carry the KaiOS banner.

To scaffold a specific repository instead of relying on the user-level install, run the workspace initializer against it. It never overwrites an existing file.

```
powershell -ExecutionPolicy Bypass -File Init-Workspace.ps1 -Path C:\work\my-repo
```

## Hook probe

Hooks fail silently when they fail, which is the worst possible property, so check them directly.

```
powershell -ExecutionPolicy Bypass -File scripts\Probe-Hooks.ps1
```

The probe pipes a sample event into the wrapper for all eight events and prints a row per event with its exit code and whether stdout was valid JSON. Every row must pass. The wrapper is built so that a missing interpreter, a missing package or a crashing hook still produces `{"continue": true}` and exit 0, so a passing probe before the Python package is in place is expected rather than a skipped test.

In VS Code, run the **Chat: Configure Hooks** command to see which hook files Copilot has actually loaded. That is the authoritative answer to whether your registry was discovered.

## First run

Start a Copilot chat and invoke the setup agent.

```
@Setup
```

Or run the skill directly with `/kaios-setup`.

Setup detects what is on the machine, shows you the result before asking anything, then interviews you about your role, your stack, and the repositories you work in. It writes a work profile, a project table with routing aliases, a path-scoped instructions file per project that needs one, an ISA seed for whatever you said you are starting on, and a config recording every optional integration as present or absent. It asks one question at a time and stops as soon as the answers stop changing what gets written. It never writes a secret anywhere, and it installs nothing.

## What is optional

KaiOS works with none of these and gets better with each. Nothing in this table is required and nothing fails when it is missing.

| Optional | What it adds | Without it |
|---|---|---|
| GitHub MCP server | Issues, pull requests and repository search as tools in chat. | Everything still works through the terminal and git. |
| Databricks CLI | Workspace, jobs, bundle and SQL operations through the audited wrapper. | The Databricks agent and skill report the CLI is absent and stop. |
| Databricks MCP server | Platform objects as chat tools instead of shell calls. | The CLI wrapper covers the same ground. |
| API keys | Whatever the API in question does. | Stored as environment-variable **names** only; KaiOS never holds a value. |
| Several enabled model vendors | Cross-vendor second looks, a third opinion on long context. | Every role collapses onto whatever model you do have. |

## Layout

```
KaiOS/
  README.md
  Install.ps1                      user-level install
  Init-Workspace.ps1               scaffold one repository
  Uninstall.ps1
  ISA.md                           this repository's own ideal state
  .github/
    copilot-instructions.md        the constitution, always loaded
    instructions/*.instructions.md path-scoped rules with applyTo globs
    agents/*.agent.md              roles pinned to model rungs
    skills/<Name>/SKILL.md         capabilities, plus bundled tools
    hooks/kaios.json               all eight chat events
    hooks/kaios.ps1                Windows wrapper around the Python runner
  .vscode/
    mcp.json.template              rendered by setup
    mcp.example.json               what a configured registry looks like
  kaios/                           Python package, standard library only
  SYSTEM/                          doctrine and templates, installed to KAIOS_HOME\SYSTEM
  scripts/                         Test-PS51.ps1, Probe-Hooks.ps1
  tests/
```

Runtime state lives under `KAIOS_HOME`, which defaults to `.kaios` in your user profile. Config, your profile and project table, memory, the ISA registry and the observability logs are all there, and none of it is ever committed. Run `python -m kaios paths` to print every resolved path.

## Models

Copilot exposes models from several vendors. KaiOS uses them by role and never by name, because a model name written into prose is wrong the moment the lineup changes.

| Role | Used for |
|---|---|
| `max` | judgment, planning, design, review, audits, work on KaiOS itself |
| `high` | execution of work that is already scoped |
| `medium` | trivial execution — formatting, mechanical edits, summaries |
| `cross` | a second look from a different vendor family than the builder |
| `third` | a third vendor's opinion, and very long context |
| `research` | reading the web and large document sets |

The registry is `SYSTEM/CONFIG/models.json`, installed to `$KAIOS_HOME/SYSTEM/CONFIG/models.json`. Each agent file carries a `kaios-role` marker on its first body line, and the registry is what decides which models that role resolves to.

```
python -m kaios models show
python -m kaios models set max "<model>,<fallback>"
python -m kaios models apply
```

`apply` rewrites the `model:` list in every agent file from the registry, so changing a lineup is one edit and one command rather than a pass over ten files. Set each role to models your organisation has actually enabled — a role pointing at a model you cannot reach just falls through to the next entry in its list.

One rule is structural rather than configurable: a second look is always a different vendor family from whoever built the thing. A model reviewing its own family's output shares its blind spots and argues for its own choices.

## Troubleshooting hooks

Hooks never write to stderr and never exit non-zero; anything that goes wrong is appended to `%KAIOS_HOME%\MEMORY\OBSERVABILITY\hook-errors.log`. Read that file first.

| Symptom | Cause | Fix |
|---|---|---|
| Every command denied, hook shown as erroring | The workspace is not the KaiOS checkout and the `kaios` package could not be imported (first field report) | `git pull` in the KaiOS clone, re-run `Install.ps1` (it copies the package to `%KAIOS_HOME%\lib` and sets `KAIOS_REPO`), open a new VS Code window |
| Hooks silent, no log lines | Hook files not discovered | Run `Chat: Configure Hooks`, confirm `chat.useHooks` is on and the workspace is trusted |
| Need hooks off right now | | Set the user environment variable `KAIOS_HOOKS_DISABLED=1` and restart VS Code; every hook then answers `{"continue": true}` |

## Uninstall

```
powershell -ExecutionPolicy Bypass -File Uninstall.ps1
```

This removes only what the installer put in your user-level Copilot directory, and it derives that list from this checkout, so anything you added yourself is left alone. Add `-WhatIf` to see the plan without touching anything.

Your KaiOS home is deliberately left in place, because it holds your memory, your ISA registry and your configuration. Deleting it takes both flags.

```
powershell -ExecutionPolicy Bypass -File Uninstall.ps1 -PurgeHome -Force
```

The `KAIOS_HOME` environment variable is never removed automatically. Clear it from System Properties if you want it gone.
