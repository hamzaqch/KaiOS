---
phase: climbing
progress: 0/38
task: "Build KaiOS: full LifeOS-class harness for Copilot in VS Code"
slug: kaios
started: 2026-09-28T00:00:00Z
updated: 2026-09-28T00:00:00Z
principal_stated_goal: "crate a framwrok simiiler to lifeos with all the hooks, agent, skill, workflows that can be used in vscode we are only allowd to install python so eveything should be in powershell or vscode … FM should not include any lifeos or personal stuff should be for work only … i want to have all the hevry stuff include eveything from lifeos expect personal stuff … drop the dashboard, and biuld also name is KaiOS, copilot allowd us to use miltimple ai model clude, gemeni, chatgpt how we are going to utitlize them, also when user first time use it it's need to help user install it self and link all mcp and cli and api, eveything should be optional for mcp, databrick cli and api, review thse userr project by intreviing them to help them biuld tyhe fm"
---

# KaiOS — work-only AI operating system for Copilot in VS Code

## Problem

The principal's work environment is Windows, VS Code, GitHub Copilot, Python, and the Databricks CLI. Nothing else may be installed. Copilot out of the box has no doctrine, no articulated done-state, no verification gates, no memory, and no role-based use of the several models it exposes. The principal wants the full weight of a LifeOS-class harness there, with every personal element removed.

## Vision

A teammate clones KaiOS, runs one PowerShell script, answers a short interview, and the next Copilot chat opens as Kai: it knows the team's projects, writes done down as claims before building, refuses to say "done" without evidence, remembers what it learned, picks the right model for each role, and guards against destructive commands. Optional integrations (MCP, Databricks, APIs) light up when linked and are never required. The euphoric surprise is a Copilot session that behaves like a disciplined senior engineer from the first prompt.

## Out of Scope

- Any dashboard or web server (dropped by principal).
- Voice, chat channels, browser automation, life-domain skills, personal identity or goals.
- Node, Bun, npm, compiled binaries, third-party Python packages.
- Anything that requires admin rights on Windows.

## Principles

- Ideal-state prompting: every skill and agent states what done looks like, not a procedure.
- Deterministic where possible: hooks and CLIs are Python; prose only carries judgment.
- Everything optional, everything documented, everything testable here on Linux with pwsh and Python.

## Constraints

- Windows PowerShell 5.1 syntax in every `.ps1`; Python 3.10+ stdlib only.
- Copilot-native discovery paths only (see `KAIOS/DOCUMENTATION/Blueprint.md`).
- Zero personal or other-system content; `tests/containment.txt` is the falsifier.

## Goal

Ship KaiOS v1.0.0 at `~/code/KaiOS`: doctrine, 25+ hooks, 25+ skills, 8+ agents with multi-model routing, a stdlib Python CLI, memory, ledger, integrity, a self-installing setup interview, optional Databricks/MCP/API linking, and tests that prove each claim on this machine.

## Features

### F0 · Cross-cutting
Why: the constraints that make it installable at work and safe to share with a team.

- [ ] ISC-1: `python -m pytest tests -q` (or `python -m unittest`) passes with zero failures. Falsifier: any failing test.
- [ ] ISC-2: `tests/test_containment.py` greps the whole repo for every term in `tests/containment.txt` (personal names, home paths, the other system's name) and finds zero hits. Falsifier: one hit.
- [ ] ISC-3: no `.py` file imports anything outside the standard library. Falsifier: `python -m kaios integrity imports` reports a non-stdlib import.
- [ ] ISC-4: every `.ps1` parses under PowerShell 5.1 rules: `scripts/Test-PS51.ps1` runs the PS parser with 5.1-only tokens banned (`??`, `?:`, `&&`, `||` at statement level). Falsifier: parser error or banned token.
- [ ] ISC-5: `git log` shows a commit per feature and the repo has no untracked build output at close. Falsifier: `git status --porcelain` non-empty.

### F1 · Doctrine
Why: Copilot needs the constitution, the Algorithm, and the verification rules loaded on every session, rewritten fresh with no personal residue.

- [ ] ISC-6: `.github/copilot-instructions.md` exists, under 12k chars, contains the response format, the five constitutional rules (output format, verification, analysis-read-only, security protocol, self-healing), the Algorithm pointer, and the routing table. Falsifier: grep for each rule heading fails.
- [ ] ISC-7: `KAIOS/ALGORITHM/LATEST` names a version whose file exists and states the run-complete claims (goal preserved, done written first, anti-claims, prerequisites probed, ambiguity resolved, evidence per claim, class sweep, ask fidelity, second look, trail, spend). Falsifier: any of those eleven ideas missing from the file.
- [ ] ISC-8: `KAIOS/RULES/Verification.md`, `SelfHealing.md`, `Philosophy.md` exist, each with freshness frontmatter and at least the rule names of their originals (modality fidelity, defer on unavailable verifier, appearance ≠ existence, reproduce before fixing, temporal fidelity, restore parity, cache fidelity; routing table for where a rule lives; intent engineering + ideal-state prompting). Falsifier: grep.
- [ ] ISC-9: `KAIOS/DOCUMENTATION/ISAFormat.md` defines the ISA sections, claim syntax, `(after:)` edges, anti-claims, fog, remaining work, and `kaios isa check` enforces it. Falsifier: a malformed ISA passes `check`.
- [ ] ISC-10: at least 6 `.github/instructions/*.instructions.md` files with `applyTo` globs (python, tests, powershell, sql/notebooks, databricks bundles, markdown docs) and each under 4k chars. Falsifier: count or frontmatter.

### F2 · Hooks
Why: doctrine that is not enforced deterministically decays; the hook layer is what makes Kai keep its promises.

- [ ] ISC-11: `.github/hooks/kaios.json` registers all eight Copilot events, each with `command` and `windows` entries pointing at the runner. Falsifier: `kaios hooks list` shows fewer than 8.
- [ ] ISC-12: `.github/hooks/kaios.ps1` reads stdin, locates python, runs `python -m kaios.hooks <Event>`, and passes stdout through; `pwsh -File .github/hooks/kaios.ps1 SessionStart < sample.json` returns valid JSON. Falsifier: non-JSON or non-zero exit.
- [ ] ISC-13: the runner never crashes the harness: a hook module that raises still yields valid JSON with `continue: true` and the error logged to `hook-events.jsonl`. Falsifier: test with a deliberately failing hook.
- [ ] ISC-14: at least 25 hook modules exist across the eight events, each with a docstring stating its rule and its test in `tests/test_hooks.py`. Falsifier: `kaios hooks list` count < 25 or a hook without a test.
- [ ] ISC-15: PreToolUse guard returns `deny` for `rm -rf /`, `git push --force` to main, `DROP TABLE`, `databricks workspace delete`, and `ask` for `databricks bundle deploy -t prod`; returns nothing for `git status`. Falsifier: table-driven test.
- [ ] ISC-16: SessionStart injects: doctrine pointer, active ISA summary, memory hot layer, time/date, and config flags, as one `additionalContext` string under 6k chars. Falsifier: test on a fixture home.
- [ ] ISC-17: Stop gate blocks (`continue: false`) when the active ISA has a claim checked `[x]` without an evidence stub, and passes otherwise. Falsifier: two fixture ISAs.
- [ ] ISC-18: `kaios hooks probe` fires all eight events with sample stdin and prints a pass table; `scripts/Probe-Hooks.ps1` does the same through the PowerShell wrapper. Falsifier: any event row not OK.

### F3 · Skills
Why: skills carry the thinking and domain capabilities that made the original heavy.

- [ ] ISC-19: at least 25 skills under `.github/skills/<Name>/SKILL.md`, each with valid frontmatter (`name` lowercase-hyphen ≤64, `description` ≤1024 containing "USE WHEN"), enforced by `tests/test_skills.py`. Falsifier: any skill failing schema.
- [ ] ISC-20: the set includes these names: isa, algorithm, cortex, create-skill, red-team, council, first-principles, science, iterative-depth, aperture-oscillation, root-cause-analysis, systems-thinking, bitter-pill, prompting, evals, hardening, research, fabric, html-report, trim, upgrade, suggest-skills, loop, optimize, kaios-setup, databricks, pr-review, verify. Falsifier: missing name.
- [ ] ISC-21: every skill body is ideal-state prompting: it states done-criteria, USE WHEN / NOT FOR, and tool contracts; `tests/test_skills.py` fails on numbered step-choreography over 8 steps without a keep-class tag. Falsifier: test.
- [ ] ISC-22: skills that need a deterministic tool ship it as `.py` under the skill folder or call `python -m kaios …`; each such script runs `--help` with exit 0. Falsifier: script without `--help`.

### F4 · Agents and multi-model routing
Why: Copilot exposes several vendors; the value is using each where it is strongest and never letting a builder grade its own work.

- [ ] ISC-23: `KAIOS/CONFIG/models.json` defines roles max, high, medium, cross, third, research with prioritized model lists, and `kaios models apply` rewrites every agent's `model:` from it. Falsifier: change the registry, apply, diff agent files.
- [ ] ISC-24: at least 9 agents: Kai (orchestrator, max), Planner (max), Builder (high), Reviewer (max, fresh context), Auditor (cross, read-only), Gemini-seat third opinion (third), Researcher (research), Setup (max), DatabricksOps (high), Verifier (high). Each has `tools`, `model`, `description`, and a `# kaios-role:` line. Falsifier: `tests/test_agents.py`.
- [ ] ISC-25: Kai can dispatch subagents: its `agents:` list names Planner, Builder, Reviewer, Auditor, Researcher, Verifier and its `tools` include `agent`. Falsifier: frontmatter check.
- [ ] ISC-26: the Council skill seats one agent per vendor family present in the registry and its SKILL.md documents the rule that a second look is always a different family from the builder. Falsifier: grep.
- [ ] ISC-27: `KAIOS/DOCUMENTATION/ModelRouting.md` explains the role rungs and which vendor is used for what, with the falsifier that no model name appears in any doctrine prose outside `models.json`. Falsifier: grep model names in `KAIOS/**.md` and `.github/copilot-instructions.md`.

### F5 · Python core
Why: deterministic tools are what let hooks and skills do real work without a runtime the workplace cannot install.

- [ ] ISC-28: `python -m kaios doctor` runs on a fresh `KAIOS_HOME` and reports every check with PASS/WARN/FAIL, exit 0 when nothing FAILs. Falsifier: run in a temp home.
- [ ] ISC-29: `kaios isa scaffold/check/frontier/status/render/list` work against fixtures; `frontier` respects `(after:)` edges and tombstoned claims. Falsifier: `tests/test_isa.py`.
- [ ] ISC-30: `kaios memory capture/search/digest/health/knowledge` write and read JSONL/Markdown under `KAIOS_HOME/MEMORY`; search finds a captured item by substring. Falsifier: `tests/test_memory.py`.
- [ ] ISC-31: `kaios ledger version bump` updates `KAIOS/VERSION` and appends to the registry; `kaios ledger log` reads it back. Falsifier: `tests/test_ledger.py`.
- [ ] ISC-32: `kaios integrity containment/docs/versions/imports` each return non-zero on a seeded violation. Falsifier: seeded fixtures.

### F6 · Setup and onboarding
Why: the first run must install KaiOS itself, link what the user has, and learn their projects, with every integration optional.

- [ ] ISC-33: `Install.ps1` copies agents, skills, hooks, instructions to `~/.copilot/*` (path overridable), creates `KAIOS_HOME`, renders absolute paths into the user-level hook JSON, and is idempotent (second run changes nothing). Falsifier: run twice under pwsh with a temp HOME and diff.
- [ ] ISC-34: `Init-Workspace.ps1 <repo>` creates `.github/{copilot-instructions.md,instructions,agents,skills,hooks}` and `.vscode/mcp.json` in the target only when absent, never overwriting. Falsifier: run on a repo with an existing file.
- [ ] ISC-35: `kaios setup detect` reports python, git, gh, databricks CLI, VS Code, PowerShell versions and presence of `.vscode/mcp.json` entries, each `found|missing`, never failing when something is missing. Falsifier: run on this machine.
- [ ] ISC-36: the `kaios-setup` skill plus Setup agent run an interview that writes `USER/PROFILE.md`, `USER/PROJECTS.md`, per-project `.instructions.md`, a project `ISA.md` seed, and `CONFIG/config.json` with optional flags for MCP servers (GitHub, Databricks), Databricks CLI profile, and API keys stored only as env-var names. Falsifier: rendered outputs from a fixture answers file via `kaios setup render --answers fixture.json`.
- [ ] ISC-37: `README.md` gives a five-minute install, the hook probe, the setup command, and a table of what is optional. Falsifier: grep for each section.

### F7 · Databricks (optional)
Why: it is the one domain tool the workplace has; wrappers make it safe and scriptable.

- [ ] ISC-38: the `databricks` skill ships `databricks_tool.py` wrapping auth check, workspace ls, jobs list/run, bundle validate/deploy (prod behind ask), SQL query via CLI, notebook export; it uses `subprocess` with argument arrays, never shell strings, and exits cleanly with a clear message when the CLI is absent. Falsifier: run with CLI absent here; grep for `shell=True`.

## Anti-claims

- A1: no file in the repo contains a personal name, home path, or the other system's name (ISC-2 is the probe).
- A2: no hook ever returns a non-JSON body or exits non-zero (ISC-12, 13).
- A3: no agent or doctrine prose names a model by name (ISC-27).
- A4: nothing requires Node, Bun, pip access to PyPI, or admin rights.

## Test Strategy

| ISC | probe | type |
|---|---|---|
| 1 | `python -m pytest tests -q` | bash |
| 2, 3, 32 | `python -m kaios integrity …` | bash |
| 4, 12, 18, 33, 34 | `pwsh -File scripts/… ` | bash |
| 6–10, 20, 26, 27, 37 | grep | bash |
| 11, 13–17, 19, 21–25, 28–31, 35, 36, 38 | pytest modules | bash |

## Decisions

- D1: Hook logic lives in Python, PowerShell is a thin wrapper, so hooks are testable on Linux and 5.1-safe by construction.
- D2: Model names live in one JSON registry; agents are rendered from it so a lineup change never edits prose.
- D3: Doctrine is rewritten, never copied, to guarantee zero personal residue.
- D4: Dashboard dropped per principal; observability is the ISA plus JSONL logs.

## Not yet specified

- Exact stdin schema per Copilot event: captured at first real run via `hook-events.jsonl`; hooks stay tolerant until then.
- Whether a Databricks MCP server is allowed at work: shipped as an optional template entry.

## Log

- 2026-09-28: ISA scaffolded; build fan-out begins.
