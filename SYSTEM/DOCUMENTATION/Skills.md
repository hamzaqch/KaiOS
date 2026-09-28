---
version: 1.0.0
last_updated: 2026-09-28T00:00:00Z
convention: kaios-freshness-v1
---

# Skills

> A skill is a capability, not a script. It says what done looks like for a class of work, when to reach for it, when not to, and hands over the deterministic tools that make it real. Everything about how to get there is left to the model, because a procedure written for one model's limits caps the next one.

## Anatomy

```
.github/skills/<PascalCaseName>/
  SKILL.md              the capability
  scripts/*.py          deterministic tools, stdlib only, each with --help
  references/*.md       reference material loaded on demand
```

Frontmatter, which is what discovery reads:

```yaml
---
name: root-cause-analysis          # lowercase-hyphen, 64 chars or fewer
description: >                     # 1024 chars or fewer, must contain "USE WHEN"
  Traces a failure to its systemic cause rather than its nearest symptom.
  USE WHEN a bug recurred, an incident needs a postmortem, "why does this keep
  happening", five whys, fault tree. NOT FOR a first-time bug with an obvious
  cause, or for designing something new.
argument-hint: "<the failure to investigate>"   # optional
user-invocable: true                             # optional
disable-model-invocation: false                  # optional
---
```

The `description` is the whole routing surface. A skill that never fires has a description problem, and a skill that fires constantly on unrelated work has the same problem in the other direction. `USE WHEN` lists the phrases and situations that should reach it; `NOT FOR` names the neighbouring skill it keeps getting confused with.

Skills are invoked as `/name` with arguments. Directory names are PascalCase; the `name:` field is lowercase-hyphen.

## What a body contains

Four things, in whatever order reads best:

1. **What done looks like** — the outcome, stated as testable criteria. This is the bulk of a good skill body.
2. **USE WHEN and NOT FOR** in prose, expanding the frontmatter with the judgment calls the one-liner cannot carry.
3. **Tool contracts** — the exact invocation of every bundled script, its flags, its output shape, and its failure modes.
4. **Verified gotchas** — non-obvious failures this class of work walks into, each with a trace to the incident or test that proved it.

What a body does not contain is numbered choreography. A body that reads "step 1, analyse the input; step 2, form a hypothesis; step 3, decide" is scripting the model rather than describing the goal, and it rots with every capability gain. The test for any procedural line: *would a smarter model make this line unnecessary?* Yes means cut it.

The exception is the four keep-classes from `../RULES/Philosophy.md`: safety gates, verified gotchas, tool contracts, and output-format contracts. A long enumerated sequence that belongs to one of those is legitimate, and it is tagged with which one so a later audit does not cut it by mistake.

## Bundled tools

A skill that needs something done deterministically ships it rather than describing it. Every bundled script is Python, standard library only, and responds to `--help` with exit code 0. Anything general enough to be reused belongs in the core instead, reached as `python -m kaios <group> <command>`.

The division: a script belongs to a skill when it only makes sense inside that capability; it belongs to the core when two skills would both want it, or when a hook would.

## The set

Twenty-eight skills across five groups.

### Method

| Skill | What it is for |
|---|---|
| `isa` | scaffolding, interviewing, checking and reconciling an Ideal State Artifact |
| `algorithm` | running the loop explicitly, and explaining what a run owes |
| `verify` | building the evidence set for a claim, and deciding which modality closes it |
| `science` | a hypothesis-first investigation with a designed experiment and honest measurement |
| `first-principles` | stripping a problem to what is actually constrained, then rebuilding from there |
| `iterative-depth` | several sequential passes over one problem through different lenses, to surface what one angle hides |
| `aperture-oscillation` | holding a question constant while shifting zoom between tactical and strategic, to find scope tension |

### Critique

| Skill | What it is for |
|---|---|
| `red-team` | adversarial attack on a plan or a design, decomposed into claims and attacked one at a time |
| `council` | one agent per vendor family debating a question in the open, with the dissent preserved |
| `root-cause-analysis` | tracing a recurring failure to a systemic cause rather than the nearest symptom |
| `systems-thinking` | finding the feedback structure that keeps generating a behaviour |
| `bitter-pill` | auditing an instruction set for over-prompting and cutting what a capable model makes unnecessary |
| `pr-review` | reviewing a change for correctness, silent failures, and test coverage |

### Engineering

| Skill | What it is for |
|---|---|
| `hardening` | strengthening a test suite with property tests and mutation checks, so claims hold over a domain rather than one input |
| `evals` | grading behaviour that no single probe can close, with deterministic assertions plus a bound rubric |
| `prompting` | writing and improving prompts as ideal-state descriptions rather than procedures |
| `optimize` | measuring a real bottleneck and improving it against a captured baseline |
| `databricks` | workspace, jobs, bundles, SQL and notebooks through the CLI, with production behind a gate |

### Knowledge

| Skill | What it is for |
|---|---|
| `cortex` | the memory system — capture, search, curate, and recall prior work |
| `research` | multi-source web research with every claim traced to a verified source |
| `fabric` | a library of focused extraction and analysis patterns over text |
| `html-report` | rendering an analysis as a self-contained, well-designed HTML page |

### System

| Skill | What it is for |
|---|---|
| `kaios-setup` | the first-run interview: profile, projects, optional integrations, and an ISA seed |
| `create-skill` | scaffolding, validating and improving a skill, so none is written by hand |
| `suggest-skills` | reading work history for recurring pain no existing skill covers, and proposing what to build |
| `trim` | shrinking an always-loaded doctrine file without dropping a directive |
| `upgrade` | pulling improvements from what the field is shipping and filtering them against current state |
| `loop` | running a prompt or a skill repeatedly on an interval or until a condition holds |

## What the tests enforce

`tests/test_skills.py` fails on:

- frontmatter missing `name` or `description`, a `name` that is not lowercase-hyphen or is over 64 characters, a `description` over 1024 characters, or a `description` with no `USE WHEN`
- a directory name that is not PascalCase
- a bundled script that does not respond to `--help` with exit code 0
- a body with more than eight numbered procedural steps and no keep-class tag naming why
- a relative link in a body that resolves to nothing
