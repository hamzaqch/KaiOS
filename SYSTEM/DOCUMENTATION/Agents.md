---
version: 1.0.0
last_updated: 2026-09-28T00:00:00Z
convention: kaios-freshness-v1
---

# Agents

> An agent is a role with a tool set and a model rung. Roles exist so that the right kind of mind does the right kind of work, and so that nobody grades their own homework. Model names never appear in an agent file by hand — `python -m kaios models apply` writes them from the registry.

## Anatomy

```
.github/agents/<Name>.agent.md
```

```yaml
---
name: Reviewer
description: Fresh-context review of a completed change against the ISA claims.
tools: [read, search, terminal]
model: [ … ]                      # generated from the registry, never hand-edited
agents: []                        # who this agent may dispatch
handoffs: [Builder]               # who it may hand work to
user-invocable: true
disable-model-invocation: false
---
# kaios-role: max

…the brief…
```

The **first body line is `# kaios-role: <role>`** and it is the source of truth for which seat the agent holds. `models apply` reads that line, resolves the role against `SYSTEM/CONFIG/models.json`, and rewrites the `model:` list. Editing `model:` by hand is a bug that the next `apply` silently reverts.

A brief states the outcome the agent owes and the evidence it must return. It never states the answer the agent is expected to reach — a reviewer told what a pass looks like reasons its way to that pass instead of driving the real path.

## Tool sets

Four sets, assigned by what the role is allowed to do.

| Set | Tools | Held by |
|---|---|---|
| read-only | read, search | anything that analyses or audits |
| build | read, search, edit, terminal | anything that produces code |
| dispatch | read, search, edit, terminal, agent | the orchestrator only |
| probe | read, search, terminal | anything that verifies without changing |

A read-only agent that could write would eventually write, and an audit that edits the thing it audits is not an audit. The permission layer enforces this rather than the brief asking politely.

## The roster

| Agent | Role | Tools | Owes |
|---|---|---|---|
| `Kai` | `max` | dispatch | the orchestrator. Holds the conversation, runs the Algorithm, writes the ISA, decides what to delegate and what to do inline, and is the only agent that dispatches others. |
| `Planner` | `max` | read-only | a scoped plan: the claims that define done, their falsifiers, the ordering edges that are real, and the prerequisites that must be probed first. Writes no code. |
| `Builder` | `high` | build | a claim closed on evidence. Takes claims that are already written and climbs them. Escalates instead of reinterpreting when a claim turns out to be wrong. |
| `Reviewer` | `max` | read-only | a fresh-context review against the goal and the claims, carrying neither the build plan nor the expected conclusion. |
| `Auditor` | `cross` | read-only | a second look from a different vendor family than the one that built the work. Returns structured findings, each with severity and a concrete reproduction. Never audits a build from its own family. |
| `ThirdSeat` | `third` | read-only | the third family's opinion — tie-breaking between two disagreeing reviews, and any job where the whole input must sit in one context window. Named for its seat, not its vendor. |
| `Researcher` | `research` | read-only | findings with every claim traced to a source fetched this run. Marks what it could not verify rather than smoothing it over. |
| `Verifier` | `high` | probe | the evidence set for a set of claims: the probe run, its real output, and a per-claim verdict of closed, open, or deferred with a reason. |
| `Setup` | `max` | build | a completed first run: profile, project table, optional integrations linked, per-project instructions, and a seeded ISA. Asks rather than assumes, and treats every integration as optional. |
| `DatabricksOps` | `high` | build | workspace, job, bundle and query work through the CLI using argument arrays. Validates before deploying and stops for approval on production, every time. |

Ten agents. `Kai` may dispatch `Planner`, `Builder`, `Reviewer`, `Auditor`, `Researcher` and `Verifier`; the rest dispatch nobody.

## The rules that make the roster worth having

**The builder never grades its own build.** A delegate that inherited the build context is the builder for this purpose — it defends its own code. An independent second look is dispatched fresh, with the goal and the claims but not the plan.

**A second look is always a different vendor family from the builder.** That is the whole reason `Auditor` sits on the `cross` seat and `ThirdSeat` on `third`. Same-family review shares the family's blind spots and finds its habits reasonable. When only one family is available, the honest record is "no independent second look was available", written into the ISA Log as a skip with a reason.

**The review scales to blast radius, and skipping is never silent.** A local refactor may skip it. Anything touching authority, secrets, shared infrastructure, or a production surface does not. Either way one Log row says what happened.

**Downshift for execution, escalate for judgment.** `max` plans and reviews, `high` executes what is scoped, `medium` does the mechanical work. An execution leg that meets real ambiguity stops and reports rather than deciding.

**A silent delegate is a failure, not a pass.** One nudge, then it is reported failed, its absence named in the run's output, and no claim closes on a report that never arrived.

**Vary the scaffold across a wide fan-out.** Past roughly four workers on open-ended work, change the family, the lens, or the brief's shape between them. Identical workers fail identically and agree while doing it.

## What the tests enforce

`tests/test_agents.py` fails on:

- missing `name`, `description`, `tools` or `model` in frontmatter
- a first body line that is not `# kaios-role: <role>`
- a role that is not in the registry
- a `model:` list that does not match what the registry resolves for that role
- an `agents:` entry naming an agent that does not exist
- a read-only role holding a write tool
