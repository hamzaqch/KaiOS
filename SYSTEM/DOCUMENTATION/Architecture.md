---
version: 1.0.0
last_updated: 2026-09-28T00:00:00Z
convention: kaios-freshness-v1
---

# Architecture

> The one-page map. Each layer has its own document; this page says what the layers are, which direction they depend on, and where a given kind of thing lives.

## What KaiOS is

A work-only operating layer for Copilot in VS Code on Windows. It takes a general coding assistant and gives it doctrine, a written definition of done, deterministic enforcement, domain capability, role-based use of several vendors' models, and memory that survives the session.

It installs with Python and PowerShell, nothing else. Every integration is optional: KaiOS works with none of them and gets better with each one linked.

## The eight layers

```
  you ──▶ Copilot session
             │
    ┌────────┴─────────────────────────────────────────────┐
    │ 1. DOCTRINE      constitution · Algorithm · rules     │  always loaded
    │ 2. HOOKS         8 events → one Python runner         │  deterministic
    │ 3. SKILLS        domain capability, invoked as /name   │  on demand
    │ 4. AGENTS        roles pinned to model rungs           │  dispatched
    ├───────────────────────────────────────────────────────┤
    │ 5. PYTHON CORE   python -m kaios — everything above    │  stdlib only
    │                  that needs to be deterministic        │
    ├───────────────────────────────────────────────────────┤
    │ 6. MEMORY        WORK · KNOWLEDGE · LEARNING · STATE   │  under KAIOS_HOME
    │ 7. LEDGER        versions, change registry, deploys    │
    │ 8. INTEGRITY     containment · cross-refs · versions   │
    └───────────────────────────────────────────────────────┘
```

Dependency direction is strictly downward. Doctrine names the CLI; the CLI never reads doctrine for behaviour. Hooks call the Python core; the core knows nothing about hooks. Nothing below layer 4 knows a model exists.

### 1 · Doctrine

`.github/copilot-instructions.md` is loaded into every session and is the highest authority: identity, output format, verification, security, self-healing, model routing, operational rules, and the routing table. `.github/instructions/*.instructions.md` add path-scoped rules through `applyTo` globs, and win only inside their own scope.

The Algorithm is versioned separately at `SYSTEM/ALGORITHM/LATEST` plus `v<version>.md`, so doctrine can point at it without pinning a version in prose. `SYSTEM/RULES/` holds the three payloads doctrine summarises: verification rules, where a learning lives, and why the system is shaped this way.

### 2 · Hooks

Eight Copilot events, one registration file, one PowerShell wrapper, one Python runner, and one module per rule. Hooks are where doctrine gets teeth: a rule that depends on the model remembering it decays, and a rule that is a checkable property of an artifact does not have to. Full inventory and merge semantics: `Hooks.md`.

### 3 · Skills

`.github/skills/<Name>/SKILL.md`, invoked as `/name`. A skill is a capability: what done looks like for a class of work, when to reach for it, when not to, and the deterministic tools that come with it. Skills state outcomes, not procedures. Inventory: `Skills.md`.

### 4 · Agents

`.github/agents/*.agent.md`. Each agent is a role — orchestrator, planner, builder, reviewer, auditor, researcher, verifier — with a tool set and a model rung resolved from the registry. Model names never appear in an agent file by hand; `python -m kaios models apply` writes them. Inventory: `Agents.md`, strategy: `ModelRouting.md`.

### 5 · Python core

`python -m kaios <group> <command>`, Python 3.10 or newer, standard library only, JSON on stdout unless `--md`. This is where everything that must be deterministic lives, which is also what makes the whole system testable without a model in the loop.

| Group | Owns |
|---|---|
| `paths` | resolving `KAIOS_HOME`, the repository root, and the active ISA |
| `isa` | scaffold, check, frontier, status, render, list |
| `memory` | capture, search, digest, health, knowledge |
| `ledger` | version bumps, the change registry, deploy events |
| `models` | the role registry and rewriting agent frontmatter from it |
| `setup` | detecting tools, writing config, rendering templates |
| `doctor` | one self-check over paths, config, hooks, and integrity |
| `integrity` | containment, documentation cross-references, version drift, imports |
| `hooks` | running an event, listing modules, probing all eight |

Exit codes are uniform: 0 success, 1 failure, 2 usage error.

### 6 · Memory

Everything that changes at runtime lives under `$KAIOS_HOME` (default `~/.kaios`) and is never committed: the work registry and per-task ISAs, reusable knowledge, reflections and incidents, and append-only observability streams. Layout and record shapes: `Memory.md`.

### 7 · Ledger

The applied half of change tracking: the current version, a registry row per change, and deploy events. Git is the changelog — the ledger exists so a session can answer "what is installed, what changed, and when" without reading git history.

### 8 · Integrity

Four checks that keep the repository honest, all runnable as `python -m kaios integrity <check>` and all wired into `doctor`: **containment** (no personal content, no home paths, no other-system names), **docs** (every cross-reference in a document resolves), **versions** (no drift between a version file and what references it), and **imports** (no module reaches outside the standard library).

## Two trees, one system

| Tree | Holds | Committed |
|---|---|---|
| the repository | doctrine, hooks, skills, agents, the Python package, templates, tests | yes |
| `$KAIOS_HOME` | config, your profile, projects, memory, an installed doctrine copy | never |

`Install.ps1` copies the repository's user-level surfaces into `~/.copilot/*` with absolute paths rendered, and creates `$KAIOS_HOME`. `Init-Workspace.ps1` drops a `.github/` scaffold into any other repository, never overwriting a file that already exists. Project ISAs stay in their own repository at `<repo>/ISA.md`; task ISAs live under `MEMORY/WORK/<slug>/`.

## What holds it together

Three contracts, each stated in exactly one place and referenced everywhere else.

- **The ISA** is the state of record for any piece of work. Format: `ISAFormat.md`.
- **The hook protocol** is the input and output shape every hook module honours. Semantics: `Hooks.md`.
- **The role registry** is the only file naming a model. Strategy: `ModelRouting.md`.

Everything else is replaceable without touching the others.
