---
name: release-review
description: Take a change from an articulated plan to a reviewed, verified release candidate without any stage grading its own work. Runs the 4-stage ReleaseReview agent workflow: plan, build, review, verify. Each stage names its input, its output, and the criteria that close it; the evidence gates refuse to pass on an assertion. USE WHEN release-review, run the release-review workflow, release-review workflow, start the release-review pipeline, resume release-review. NOT FOR a single-shot task one agent finishes in one pass, editing one line of an existing pipeline, or choosing which model runs a stage (the role registry decides).
argument-hint: "<the work item to run through the workflow>"
---

# ReleaseReview

Take a change from an articulated plan to a reviewed, verified release candidate without any stage grading its own work.

## What done looks like

- Every stage below ran, with its `after` dependencies satisfied first.
- Each stage produced the output named in the table, and each done criterion is closed on evidence a reader can re-run.
- Every `evidence` gate was closed by tool output in the trail, never by a claim that it would pass.
- Every `ask` gate stopped and got a human answer before the next stage started.
- None of the anti-claims below is true at the end.

## Stages

| # | stage | agent (role) | in | out | gate | after | done when |
|---|---|---|---|---|---|---|---|
| 1 | `plan` Write done down | Planner (max) | the change request, as an issue or a prompt | an ISA whose claims are falsifiable | `ask` | - | Every claim in the ISA names the probe that closes it.; At least one anti-claim states what must not become true. |
| 2 | `build` Take the frontier claims | Builder (high) | the ISA from the plan stage | a working tree that takes the claims on the frontier | `auto` | plan | Every claim taken this pass has a code change behind it.; The test suite ran and its output is captured verbatim. |
| 3 | `review` Second look from another family | Auditor (cross) | the diff plus the ISA | a findings list ranked by severity | `auto` | build | Every finding names the file and the line it applies to.; The reviewing role is a different vendor family from the builder. |
| 4 | `verify` Close the claims on evidence | Verifier (high) | the ISA and the reviewed tree | an evidence trail, one entry per closed claim | `evidence` | review | Each claim marked done quotes the command and its output.; No claim is closed on an assertion that it would pass. |

## Gates

| gate | meaning |
|---|---|
| `auto` | the stage closes its own criteria and hands off |
| `ask` | the stage stops and waits for a human answer before handing off |
| `evidence` | the stage may not pass until tool output for every criterion is in the trail |

## Anti-claims

- No stage reports done for a criterion whose probe was never run.
- The builder never reviews its own diff.
- No claim is closed from memory of an earlier run.

## How to run

Pick the **ReleaseReview** agent in the agent picker and describe the work item, or type `/release-review <work item>` to run this skill directly. The orchestrator dispatches each stage to the agent in the table and holds the gates. Run state lives at `$KAIOS_HOME/MEMORY/STATE/workflows.json`.

## Spec

The machine-readable spec is [workflow.json](agent-release-review.workflow.json). Validate it after any edit:

```
python .github/skills/CreateWorkflow/workflow_tool.py validate .github/skills/ReleaseReview/workflow.json
```

---

## About this example

This file is `workflow_tool.py scaffold` output, copied in unchanged except for its relative
links, which are repointed at the sibling example files so they resolve here. In a real
repository the generator writes them as `workflow.json`, because the artifacts sit at their real paths.
