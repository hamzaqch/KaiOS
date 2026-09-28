---
name: kaios-setup
description: "The first-run interview. Detects what the machine already has, learns who the engineer is and what their team owns, maps the models their organisation actually enabled onto the role registry, links each optional integration or records it as deliberately skipped, then interviews them about each project and writes the profile, the project table, per-project instructions and a project ISA seed. Secrets are never written to disk, only the names of environment variables. USE WHEN setup, first run, install, onboard me, get me started, configure KaiOS, set up KaiOS, initialise, link my integrations, connect GitHub, connect the platform CLI, which models should I use, register my projects, add a project, tell you about my projects, redo the setup, my config is empty, nothing knows about my repos. NOT FOR copying files onto the machine (the installer script does that), editing a single config value by hand, or creating a new skill (use create-skill)."
argument-hint: "[full|models|integrations|projects]"
---

# KaiosSetup — the first run

## What this produces

Six things, and the setup is not done until each one exists or is recorded as skipped:

| Artefact | Holds |
|---|---|
| `$KAIOS_HOME/CONFIG/config.json` | what was detected, every optional flag, and the project list |
| `$KAIOS_HOME/CONFIG/models.json` | role to model mapping, from the models this organisation enabled |
| `$KAIOS_HOME/USER/PROFILE.md` | who the engineer is, their role, team and stack |
| `$KAIOS_HOME/USER/PROJECTS.md` | the project table and the routing aliases |
| `.github/instructions/<project>.instructions.md` | per-project rules, scoped by glob |
| `<project>/ISA.md` | a seeded ideal state for the first project |

## Done looks like

- `python -m kaios doctor` reports no FAIL.
- The config has no empty optional block: each integration is either linked or carries an explicit skip.
- `python -m kaios models show` maps all six roles to models that actually appear in this engineer's picker.
- The project table's aliases resolve: saying a nickname routes to the right path.
- The first project has an ISA with a Goal and at least one claim, derived from the engineer's own answer about what done means.
- No secret value exists anywhere on disk. Only environment variable names.

## USE WHEN

KaiOS was just installed, the config is empty, a new project needs registering, the model lineup changed, or an integration needs linking or unlinking.

## NOT FOR

Copying files onto the machine: the installer script does that, and it runs before this. Editing one config value, which is a one-line change. Creating a skill (`create-skill`).

## Never write a secret

<!-- keep: safety-gate -->

This is the one rule with no exception and no judgement call attached.

1. Config stores the **name** of an environment variable that holds a credential. Never the value.
2. If the engineer offers a token, a key, a password or a connection string, stop and ask for the variable name instead. Do not echo the value back, do not put it in a file, do not put it in a command.
3. Authentication that needs a browser or a prompt is run by the engineer in their own terminal. Report the command for them to run; never attempt an interactive login from here.
4. Before finishing, confirm nothing written this session contains a credential-shaped string.

A config that cannot be committed to a private repository without redaction has been written wrongly.

## The flow, as an outcome

Each phase ends in a written file, so an interrupted setup resumes from what is on disk rather than from the conversation. The full question bank is in [references/questions.md](references/questions.md).

**Detect, then report.** Run `python -m kaios setup detect` and show the result as a found-or-missing table: runtime, version control, the editor, the shell version, the platform CLI, and whether an MCP config already exists. Ask only whether anything expected is missing. Never ask for something that was detected.

**Learn the engineer.** Name to use in a response, role, team and what that team owns, the daily stack, and how they want to be talked to. Short, and it becomes the profile.

**Map the models.** The picker's contents differ by organisation, so ask what is actually in it rather than assuming a lineup. Then assign: strongest reasoner to **max**, workhorse to **high**, fast and cheap to **medium**, a different vendor from max to **cross**, a third vendor if present to **third**, and the best long-context model to **research**. Write it with `python -m kaios models set <role> <model,…>` and propagate with `python -m kaios models apply`. When only one vendor is enabled, say plainly that the cross-family second look degrades to a same-family review, which is weaker.

**Offer each integration separately.** Four of them, each individually skippable, each skip recorded as a skip so a later session does not ask again.

| Integration | What linking means | What is stored |
|---|---|---|
| GitHub MCP | an entry is written into the workspace MCP config | the entry, referencing an env var name |
| Platform CLI | the engineer runs the interactive login themselves, in their own terminal | the profile name only |
| Platform MCP | an optional placeholder entry, only if the organisation runs one | the entry |
| API keys | nothing is connected; KaiOS learns the variable name | the variable name and its purpose |

For the platform CLI, ask which profile is production. That answer is what lets the deploy approval gate fire on the right target, and without it the gate guesses from the target name alone.

**Interview each project.** One at a time, stopping when the engineer says that is all of them. Name, path, purpose, stack, deploy command, conversational aliases, repository URL, what done usually means here, and what goes wrong more than once. The last two are the valuable ones: the done-definition becomes the ISA seed, and the recurring problems become the project's instruction file.

**Write and render.** `python -m kaios setup write-config <json>` persists the answers; `python -m kaios setup render` produces the profile, the project table, the per-project instruction files and the MCP entries with absolute paths resolved. Then seed the first project's ISA with `python -m kaios isa scaffold --project` and offer `/isa interview` for a proper grilling of its ideal state.

**Show the work.** List every path written and one line on what is in it. A setup that ends without showing its output leaves the engineer unable to correct a wrong answer.

## Tool contracts

<!-- keep: tool-contract -->

| Command | Contract |
|---|---|
| `python -m kaios setup detect` | reports each tool as found or missing with its version. Never fails because something is absent. |
| `python -m kaios setup write-config <json>` | persists the answers into `CONFIG/config.json`. Merges rather than replacing, so a partial re-run does not lose earlier answers. |
| `python -m kaios setup render [--answers file.json]` | renders the profile, the project table, per-project instruction files and MCP entries. With `--answers` it renders from a fixture instead of the live config, which is how this flow is tested. |
| `python -m kaios models set <role> <model,…>` | writes one role's prioritised model list |
| `python -m kaios models apply` | rewrites every agent's model list from the registry |
| `python -m kaios isa scaffold --slug S --goal G --project` | seeds the project ISA |
| `python -m kaios doctor` | the final check; exit 0 when nothing FAILs |

The config schema, with every optional block:

```json
{
  "user":   { "name": "", "role": "", "team": "", "stack": [] },
  "optional": {
    "mcp":            { "github": false, "databricks": false },
    "databricks_cli": { "enabled": false, "profile": "" },
    "apis":           { "<name>": { "env_var": "", "purpose": "" } }
  },
  "projects": [
    { "name": "", "path": "", "url": "", "deploy": "", "stack": [], "aliases": [] }
  ]
}
```

A worked fixture, including the project fields that render into prose: [references/answers-example.json](references/answers-example.json).

One rendering rule worth knowing before you write an answers file. A string field renders as exactly one bullet and is never split on punctuation, so a sentence containing commas stays whole. When you want several bullets, pass a JSON array. That is why `done_means` is a single sentence and `pain_points` is a list in the fixture.

## Constraints and gotchas

- Everything is optional. KaiOS has to work with zero integrations linked, and the interview must never imply otherwise or stall waiting for one.
- Record a skip as a skip. An empty value is indistinguishable from an unasked question, and the next session will ask again, which is how an onboarding becomes annoying.
- Never ask for anything detection already answered. Asking the engineer their runtime version after printing it reads as not having looked.
- Keep it short. Six well-chosen questions that get answered beat twenty that get abandoned. The interview can be resumed; a first impression cannot.
- Write paths in the platform's own form, and never assume a drive letter or a folder layout. Read the path the engineer gives you.
- Re-running setup is safe and normal. Merge into the existing config, show what changed, and never silently drop an earlier answer.
- A project instruction file needs a glob that actually matches. Check it against a real path in that project before finishing, or the rules never load.
