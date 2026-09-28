---
version: 1.0.0
last_updated: 2026-09-28
convention: kaios-freshness-v1
---

# The interview

Ten questions is the ceiling, not the target. Every answer already in the request is an answer
you do not ask for, and the tool's defaults cover the rest. The machine-readable form of these
banks is `workflow_tool.py questions --kind <kind>`; this file is the same content with the
reasoning spelled out for a human reading it.

## Question zero, always: which kind?

Ask what runs the thing. The answer picks the kind and nothing else in the interview makes
sense before it.

| if the user says | kind |
|---|---|
| "chain these agents", "plan then build then review", "stages", "handoffs" | agent |
| "on every push", "on a schedule", "in CI", "when a pull request opens" | actions |
| "a job", "tasks on a cluster", "a notebook pipeline", "deploy the bundle" | databricks |

When the answer is vague, say the default out loud and let them redirect: **the KaiOS agent
workflow is the default**. Vague requests are nearly always about getting the model to do
several things in order, which is what the agent kind is.

A request can be two kinds at once. "Run my tests in CI and then have an agent review the
failures" is an Actions workflow plus an agent workflow, built one at a time. Say so rather
than blending them into one artifact that is neither.

## Kind 1 — KaiOS agent workflow

| # | question | why it matters |
|---|---|---|
| 1 | In one sentence, what does this workflow make true that is not true now? | The goal is what every stage is measured against. Without it the stages become a procedure nobody can grade. |
| 2 | What should it be called, in PascalCase? | Becomes the skill directory, the lowercase-hyphen skill name, and the orchestrator agent file. |
| 3 | Walk me through the stages in order: a short title and the role for each. | Stages are the unit of handoff. One stage per change of role or change of artifact; anything finer is choreography. |
| 4 | For each stage, what goes in and what comes out? | A stage whose output is not named cannot hand off, and the next stage has nothing to check. |
| 5 | For each stage, how would someone else prove it is done? | These become `done_criteria`. Falsifiable criteria are the only thing that stops a stage declaring victory. |
| 6 | Which stages pass on their own, which stop and ask, which must show tool output? | The three gates are `auto`, `ask`, `evidence`. At least one `evidence` gate is required or nothing is ever verified. |
| 7 | Does any stage depend on more than the one before it? | The `after` edges make order explicit and let independent stages run in parallel. They must stay acyclic. |
| 8 | What must never become true while this runs? | Anti-claims catch what passing criteria will not: the shortcut, the self-review, the silent scope change. |
| 9 | Who checks the builder's work, and is it a different vendor family? | A stage reviewing its own family's output shares its blind spots. The `cross` and `third` roles exist for this. |
| 10 | Will you start it from the agent picker or the slash command? | Decides which artifact is the front door and what the argument hint should say. |

Skip 7 when the flow is a straight line. Skip 10 when they already said "I want a command".

## Kind 2 — GitHub Actions workflow

| # | question | why it matters |
|---|---|---|
| 1 | What should happen automatically, and what breaks today because it does not? | A workflow with no failure it prevents is decoration. |
| 2 | Is this a test run, a bundle deploy, or a scheduled task? | Picks the template: `python-tests`, `databricks-bundle-deploy`, `scheduled-job`. |
| 3 | What triggers it: push, pull request, cron, manual dispatch? | The `on:` block is the whole contract with GitHub. Everything else is steps. |
| 4 | Which runner, and does it need a specific interpreter version? | Runner and version decide whether the steps are portable or silently shell-specific. |
| 5 | What is the exact command that proves the job worked? | A workflow whose command cannot fail proves nothing. This is the falsifier. |
| 6 | What credentials does it need, and are they repository secrets already? | Secrets belong in `env`, referenced by name, never interpolated into a `run` line the log would print. |
| 7 | Does it touch a protected target such as production? | A prod job needs an `environment` for approval, or the workflow can deploy without anyone agreeing to it. |
| 8 | Who should notice when it fails, and how? | A red run nobody looks at is a disabled test with extra steps. |

## Kind 3 — Databricks job workflow

| # | question | why it matters |
|---|---|---|
| 1 | What does this job produce, and who consumes it? | Names the job and decides how loud failure needs to be. |
| 2 | Which bundle does it belong to, and does a `databricks.yml` already exist? | The resource file is meaningless outside a bundle. A missing bundle root gets scaffolded with dev and prod targets. |
| 3 | List the tasks in order, with a `task_key` for each. | `task_key` is the identity of a task; duplicates make the dependency graph ambiguous and the deploy rejects them. |
| 4 | For each task: notebook, Python wheel, or SQL? | Exactly one task type per task. Two types is a task that does not deploy. |
| 5 | Which tasks wait on which? | `depends_on` must point at real task keys and stay acyclic, or validation rejects the job. |
| 6 | Does it run on a schedule, or only when triggered? | A scheduled job needs a quartz expression and an explicit timezone, or it drifts twice a year. |
| 7 | Where should failure notifications go? | Jobs fail at night. The notification is the only reason anyone finds out. |
| 8 | Who may deploy this to prod, and through what? | The prod target should be reached through a reviewed pipeline with an approval gate, not from a laptop. |

## Recording the answers

Write the answers into a JSON file shaped like the examples one directory up, then scaffold
from it. Two reasons: the answers file is re-runnable when the shape changes, and it is the
diffable record of what the user actually asked for when the artifact drifts later.
