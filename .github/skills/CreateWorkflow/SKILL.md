---
name: create-workflow
description: Build a validated, runnable workflow of the right kind with its done-criteria written down. Interviews in under ten questions, picks one of three kinds (a KaiOS agent workflow of staged agents, a GitHub Actions workflow, or a Databricks job in a bundle), scaffolds the artifacts, then validates them with a tool that exits non-zero on a broken shape. USE WHEN build a workflow, create workflow, automate this, multi-step pipeline, github actions, databricks job, orchestrate agents, chain agents with handoffs, add a CI job, schedule a nightly run, wire stages together, validate my workflow file, turn this into a pipeline. NOT FOR single-shot tasks one pass finishes, creating a plain skill with no stages (use create-skill), editing one line of an existing pipeline, or choosing which model runs a stage (the role registry decides that).
argument-hint: "<what the workflow should accomplish>"
---

# Create Workflow

At work "workflow" means three different things. This skill finds out which one the user means,
asks only what it cannot infer, writes the artifacts, and proves they are well-formed before
saying anything is done.

## USE WHEN / NOT FOR

USE WHEN the user wants something built that runs in more than one step: build me a workflow,
automate this, chain these agents, add a CI job, schedule a nightly run, turn this into a pipeline,
orchestrate the review. Also use it when they say "workflow" and you cannot yet tell which of the
three kinds they mean, since finding that out is the first thing this skill does, and when they
have a workflow file already and want to know whether it is well-formed.

NOT FOR a task that one pass finishes, where a workflow is ceremony around a single action. NOT FOR
creating a plain skill with no stages, which is what create-skill is for: when the answer to "what
are the stages" is "there is one", the user wants a skill and should be sent there. NOT FOR editing
one line of a pipeline that already exists, where opening the file beats an interview. NOT FOR
deciding which model runs a stage, which the role registry settles and no interview should reopen.

## What done looks like

- The user said what they wanted once, answered at most ten questions, and has files they can run.
- The kind is the right one, and the user knows which kind they got and why.
- Every artifact for that kind exists on disk, at the path the harness discovers it at.
- `workflow_tool.py validate <path>` exits 0 for every file written. A workflow that has not been
  validated is not built yet, and neither is one whose validation you describe instead of run.
- Done-criteria are written into the artifact itself, not left in the conversation. For an agent
  workflow that is `done_criteria` per stage; for the other two it is the command that fails when
  the job is broken.
- Anything the tool defaulted for the user is said out loud. The scaffold reports its own
  assumptions in `notes`; those notes are for the user, not for the log.
- The user knows how to start it, in the words of the surface they start it from.

## The three kinds

⚠️ **Default when the user is vague: the KaiOS agent workflow.** Say the default out loud and let
them redirect. Vague requests are nearly always "get the model to do several things in order",
which is exactly that kind.

| kind | it is | artifacts | what runs it |
|---|---|---|---|
| `agent` | stages of thinking or building, each by a role, with gates between | `.github/skills/<Name>/SKILL.md`, `.github/skills/<Name>/workflow.json`, `.github/agents/<Name>.agent.md` | the editor: the orchestrator agent, or `/<name>` |
| `actions` | something that must run on a push, a pull request, a schedule, or a dispatch | `.github/workflows/<name>.yml` | GitHub runners |
| `databricks` | tasks on Databricks compute with dependencies, shipped in a bundle | `resources/<name>.job.yml`, plus `databricks.yml` when absent | Databricks Jobs, via the CLI bundle commands |

Ask what runs the thing and the kind falls out. "Chain these agents" is `agent`. "On every push"
is `actions`. "A job with tasks on a cluster" is `databricks`. A request that is two kinds at once
is built one kind at a time and said to be two, never blended into one artifact that is neither.

## The interview

The question banks live in [references/questions.md](references/questions.md), with the reason each
question exists, and machine-readably behind `questions --kind <kind>`. Read the banks; do not
read them aloud. Ten is the ceiling. Every answer already in the request is a question you skip,
and the tool has a defensible default for everything else.

Two answers are worth pushing on when they come back thin, because the tool cannot invent them:
what proves each stage or job is done, and what must never become true while it runs. A workflow
whose success cannot be distinguished from its failure was not worth building.

Write the answers to a JSON file shaped like the example for that kind
([agent](references/answers-example-agent.json),
[actions](references/answers-example-actions.json),
[databricks](references/answers-example-databricks.json)), then scaffold from it. The answers file
is re-runnable when the shape changes and is the diffable record of what was actually asked for.
The artifacts those three answers files produce are checked in under
[references/examples/](references/examples/README.md), so the user can see the destination before
answering anything.

## Tool contracts

<!-- keep: tool-contract -->

Run from the repository root. Standard library only, JSON on stdout, exit 0 ok, 1 invalid or
failed, 2 usage.

| command | contract |
|---|---|
| `python .github/skills/CreateWorkflow/workflow_tool.py kinds` | the three kinds, when to use each, and which is the default |
| `... questions --kind agent\|actions\|databricks` | the question bank for that kind, each entry with why it matters |
| `... scaffold --kind K --answers answers.json --out <repo-root>` | writes that kind's artifacts under the repo root and prints `written`, `skipped`, `notes`. Existing files are skipped, never clobbered, unless `--force` |
| `... validate <path>` | detects the kind from the filename and shape; exit 0 valid, exit 1 with a `findings` array naming code, message, and location |
| `... render --spec workflow.json --md` | the stage table markdown for a skill body, regenerated from the spec |
| `... runs start --name N` / `runs finish --name N --status ok\|failed` / `runs list` | run history in `$KAIOS_HOME/MEMORY/STATE/workflows.json` |

`--kind` on `scaffold` is optional when the answers file carries a `kind` field. `KAIOS_HOME`
comes from the environment and falls back to a `.kaios` directory in the user profile.

## Validation gates

Validation is what separates a workflow from a file that looks like one. Every gate below is
enforced by the tool, not by reading:

- **Agent spec** — unique stage ids; `after` references that exist and stay acyclic; at least one
  done criterion per stage; `gate` in auto, ask, evidence; `role` in the registry's six; at least
  one stage carrying the `evidence` gate; a non-empty `anti_claims` array.
- **Actions** — top-level `name`, `on`, `jobs`; `runs-on` and a non-empty `steps` on every job;
  `uses` or `run` on every step, never both.
- **Databricks** — unique `task_key`s; `depends_on` references that exist and stay acyclic;
  exactly one task type per task; a `databricks.yml` above the resource with a `prod` target.

A finding is a bug in the artifact, not in the tool. Fix the artifact and re-validate rather than
arguing with the finding or editing the validator.

## Safety gates

- A job that deploys to prod carries an `environment`, so that environment's protection rules are
  the approval gate. The validator reports an unprotected prod deploy as a finding. In an agent
  workflow the equivalent is an `ask` gate on the stage that ships.
- Credentials go in `env`, referenced by name. A secret interpolated into a `run` line is a
  finding, because the runner log is the first place it appears.
- Never write a credential value into any artifact. Not a token, not a host, not a connection
  string: the name of the variable is the whole contribution.
- Scaffolding never overwrites. A path that already exists comes back in `skipped`, and the user
  decides whether to pass `--force`.
- The reviewing stage of an agent workflow is never the stage that built the work, and a second
  look comes from a different vendor family than the builder. Roles, not model names, carry this.

## Running the result

An agent workflow has two front doors, and the user should be told the one they asked for. Pick
the orchestrator agent by name in the agent picker and describe the work item, and it dispatches
each stage to the agent named in the stage table and holds the gates. Or type `/<name> <work item>`
to invoke the generated skill directly, which is the lighter door when the flow is short. The
`handoffs` in the orchestrator's frontmatter carry the edges; the stage table in the generated
`SKILL.md` is the contract a human reads.

An Actions workflow runs when its `on` events fire, plus manually through the dispatch entry that
every template includes. A Databricks job is deployed by validating the bundle against the dev
target first, then deploying to the target whose protection you already decided on.

Track long flows with `runs start` and `runs finish` so the state file answers "did this run, and
how did it end" without anyone reconstructing it from a transcript.
