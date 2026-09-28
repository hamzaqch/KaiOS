---
version: 1.0.0
last_updated: 2026-09-28T00:00:00Z
convention: kaios-freshness-v1
---

# KaiOS Blueprint — the shared build contract

> Every builder reads this first. It is the one place the repo layout, the CLI surface, the hook protocol, and the naming rules are defined. If a builder needs something not here, they add it here in the same change.

## What KaiOS is

KaiOS is a work-only AI operating system for GitHub Copilot in VS Code on Windows. It moves an engineer's work from current state to ideal state: every task articulates "done" as falsifiable claims (an ISA), the Algorithm climbs those claims on tool evidence, hooks enforce the doctrine deterministically, skills carry domain capability, agents carry roles pinned to the right model, and memory keeps what was learned. It contains nothing personal: no identity, no life goals, no home paths, no references to any other system.

## Hard constraints (F0 — every builder)

- **Windows first.** Windows PowerShell 5.1 syntax for every `.ps1` (no `??`, no ternary, no `&&`/`||` chaining, no `pwsh`-only cmdlets). Test with `pwsh` here; it must also run on 5.1.
- **Python 3.10+ standard library only.** No third-party imports anywhere in `kaios/`. `pip` is not assumed to reach PyPI.
- **No Node, no Bun, no npm, no compiled binaries.** Everything is `.md`, `.json`, `.ps1`, `.py`.
- **Zero personal content.** No people's names, no user home paths, no other-system names in prose or code. The word list in `tests/containment.txt` is grepped by `tests/test_containment.py`; a hit fails the build. Write fresh prose; never paste from another system.
- **Copilot-native surfaces only.** Instructions, agents, skills, hooks, MCP config exactly where the VS Code docs discover them (see § Copilot surfaces).
- **Everything optional.** MCP servers, Databricks CLI, any API key: KaiOS works with none of them and gets better with each.

## Repo layout

```
KaiOS/
  README.md                       # what it is, 5-minute install, first run
  Install.ps1                     # user-level install → ~/.copilot/* + $KAIOS_HOME
  Init-Workspace.ps1              # drop .github/ + .vscode/ scaffold into any repo
  Uninstall.ps1
  .github/
    copilot-instructions.md       # the constitution + routing table (always loaded)
    instructions/*.instructions.md # path-scoped rules (applyTo globs)
    agents/*.agent.md             # roles pinned to model rungs
    skills/<Name>/SKILL.md        # capabilities (+ bundled scripts/, references/)
    hooks/kaios.json              # all 8 events → one runner
    hooks/kaios.ps1               # Windows wrapper: stdin → python -m kaios.hooks <Event>
  .vscode/mcp.json.template       # optional MCP servers, rendered by setup
  kaios/                          # Python package (stdlib only)
    __main__.py  cli.py           # `python -m kaios <command>`
    paths.py                      # KAIOS_HOME resolution, repo-root discovery
    isa.py                        # parse/scaffold/check/frontier/render ISA.md
    memory.py                     # capture/search/digest, hot layer, KNOWLEDGE
    ledger.py                     # versioning, update registry, deploy events
    models.py                     # role→model registry, render agent frontmatter
    setup.py                      # detect tools, write config, render templates
    doctor.py                     # self-check: paths, config, hooks, integrity
    integrity.py                  # containment grep, doc cross-refs, version drift
    hooks/__init__.py  __main__.py  runner.py   # event dispatcher
    hooks/<event_snake>/<HookName>.py            # one hook per file
  SYSTEM/                         # doctrine + templates, installed to $KAIOS_HOME/SYSTEM (named SYSTEM, not KAIOS, because kaios/ and SYSTEM/ collide on Windows)
    ALGORITHM/LATEST, v1.0.0.md
    RULES/Verification.md SelfHealing.md Philosophy.md
    DOCUMENTATION/*.md
    TEMPLATES/ISA.md PROJECT_INSTRUCTIONS.md PROJECTS.md CONFIG.json
    CONFIG/models.json            # role → prioritized model list
  scripts/*.ps1                   # helper entry points (Test-Hooks.ps1, Probe-Hooks.ps1)
  tests/                          # pytest (stdlib unittest-compatible) + Test-*.ps1
```

## KAIOS_HOME (runtime state, never committed)

`$env:KAIOS_HOME` (default `~/.kaios`; the env var keeps its name) holds everything that changes at runtime:

```
~/.kaios/
  CONFIG/config.json      # what setup detected + user choices (all optional flags)
  CONFIG/models.json      # user's copy of the model registry (edited by setup)
  USER/PROFILE.md         # work profile from the setup interview (role, team, stack)
  USER/PROJECTS.md        # project table + routing aliases
  MEMORY/WORK/<slug>/ISA.md         # task ISAs
  MEMORY/STATE/work.json            # ISA registry (mirrors every ISA write)
  MEMORY/KNOWLEDGE/*.md             # reusable facts, typed frontmatter
  MEMORY/LEARNING/REFLECTIONS/*.jsonl  INCIDENTS/*.md
  MEMORY/OBSERVABILITY/hook-events.jsonl  tool-events.jsonl  ask-fidelity.jsonl
  SYSTEM/                  # installed doctrine copy (ALGORITHM, RULES, TEMPLATES)
```

Project ISAs live at `<repo>/ISA.md`. `kaios paths` prints all resolved paths as JSON.

## CLI surface (`python -m kaios <group> <cmd>`), all output JSON unless `--md`

| Group | Commands |
|---|---|
| `paths` | print resolved paths |
| `doctor` | full self-check; exit 1 on any FAIL |
| `isa` | `scaffold --slug S --goal G [--project]` · `check <path>` (completeness, falsifiers, anti-claims, id stability) · `frontier <path>` (takeable claims) · `status <path>` · `render <path> --md` · `list` |
| `memory` | `capture --kind K --text T` · `search Q` · `digest [--since]` · `health` · `knowledge add/find` |
| `ledger` | `version [bump patch|minor|major]` · `record --kind K --summary S` · `log` |
| `models` | `show` · `set <role> <model,...>` · `apply` (rewrites `model:` in every agent file from the registry) |
| `setup` | `detect` (python, git, gh, databricks, code, pwsh version, MCP servers present) · `write-config <json>` · `render` (mcp.json, agents, hooks wrappers with absolute paths) |
| `integrity` | `containment` · `docs` · `versions` |
| `hooks` | `run <Event>` (stdin→stdout) · `list` · `probe` (fires each event with sample stdin) |

Exit codes: 0 ok, 1 failure, 2 usage.

## Hook protocol

`.github/hooks/kaios.json` is `{"version": 1, "hooks": {"<Event>": [ …entries… ]}}` and registers all eight Copilot events. Each entry runs the same wrapper with the event name:

```json
{ "type": "command",
  "command": "python3 -m kaios.hooks SessionStart",
  "windows": "powershell -NoProfile -ExecutionPolicy Bypass -File .github/hooks/kaios.ps1 SessionStart",
  "timeout": 20 }
```

The runner (`kaios/hooks/runner.py`):

1. Reads all stdin as JSON (tolerant: empty stdin → `{}`); appends the raw event to `MEMORY/OBSERVABILITY/hook-events.jsonl` so the real schema is always discoverable.
2. Loads every module in `kaios/hooks/<event_snake>/` (alphabetical). Each exposes `run(event: dict, ctx: Context) -> HookResult | None`.
3. Merges results: `additionalContext` strings joined with blank lines; `permissionDecision` takes the most restrictive (`deny` > `ask` > `allow`); `continue` false if any says false; `updatedInput` last-writer.
4. Prints one JSON object. On any hook exception: log it, never crash the harness, continue.

Output shapes (compatible with both hook dialects VS Code accepts):

```json
{ "continue": true, "additionalContext": "…" }
{ "hookSpecificOutput": { "hookEventName": "PreToolUse", "permissionDecision": "ask", "permissionDecisionReason": "…" } }
{ "continue": false, "stopReason": "…" }
```

Input fields hooks may rely on, all optional: `hook_event_name`, `session_id`, `cwd`, `timestamp`, `tool_name`, `tool_input` (dict; for shell tools look for `command`; for edit tools `filePath`/`file_path`, `content`/`newString`), `tool_response`, `prompt`/`user_prompt`, `stop_hook_active`. Always `event.get(...)`.

`Context` gives: `home` (KAIOS_HOME), `repo` (git root of cwd or None), `config` (dict), `active_isa` (path or None), `now`.

## Copilot surfaces (where things must live)

- Instructions: `.github/copilot-instructions.md` (always on) + `.github/instructions/*.instructions.md` with `applyTo`.
- Agents: `.github/agents/*.agent.md` — frontmatter `name, description, tools, model (string or prioritized list), agents, handoffs, user-invocable, disable-model-invocation, hooks`.
- Skills: `.github/skills/<name>/SKILL.md` — frontmatter `name (lowercase-hyphen, ≤64), description (≤1024, "USE WHEN …")`, optional `argument-hint, user-invocable, disable-model-invocation`. Bundled files referenced by relative link. Invoked as `/name args`.
- Hooks: `.github/hooks/*.json`.
- MCP: `.vscode/mcp.json`.
- User level (Install.ps1 copies with absolute paths rendered): `~/.copilot/agents`, `~/.copilot/skills`, `~/.copilot/hooks`, `~/.copilot/instructions`.

## Multi-model routing

Copilot exposes models from several vendor families. KaiOS uses them by ROLE, never by name in prose. The registry is `SYSTEM/CONFIG/models.json`: it maps six roles (`max` judgment/planning/review/audits, `high` execution of scoped work, `medium` trivial execution, `cross` second look from a different family than the builder, `third` third-vendor opinion and very long context, `research`) to prioritized model lists, plus a `families` map keyed by name prefix. Model names live ONLY in that file.

Each agent file carries `<!-- kaios-role: <role> -->` as its first body line (the `# kaios-role:` spelling is also accepted); `python -m kaios models apply` rewrites its `model:` list from the registry. Setup lets the user pick from the models their org enabled. Council runs one seat per family. A second look is always a different family from the builder.

## Naming and style

- Skills/agents/hooks/tools in PascalCase directory names; SKILL `name:` in lowercase-hyphen.
- Every SKILL.md: what it does, USE WHEN / NOT FOR, ideal-state prompts (what done looks like), bundled tool contracts. No step-by-step choreography.
- Plain prose. No marketing words.
- Docs frontmatter: `version`, `last_updated` (ISO), `convention: kaios-freshness-v1`.
