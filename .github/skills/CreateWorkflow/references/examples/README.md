---
version: 1.0.0
last_updated: 2026-09-28
convention: kaios-freshness-v1
---

# Rendered examples

Every file here was produced by `workflow_tool.py scaffold` from the matching answers file
one directory up, then copied in unchanged. They are reference material, not live artifacts:
the filenames are deliberately not the names the real files carry, so nothing here is
discovered as a skill, an agent, a workflow, or a bundle resource.

| example | rendered from | lands in a real repo as |
|---|---|---|
| `agent-release-review.workflow.json` | `answers-example-agent.json` | `.github/skills/ReleaseReview/workflow.json` |
| `agent-release-review-skill.md` | `answers-example-agent.json` | `.github/skills/ReleaseReview/SKILL.md` |
| `agent-release-review-orchestrator.md` | `answers-example-agent.json` | `.github/agents/ReleaseReview.agent.md` |
| `actions-python-tests.yml` | `answers-example-actions.json` | `.github/workflows/python-tests.yml` |
| `actions-databricks-bundle-deploy.yml` | the `databricks-bundle-deploy` template | `.github/workflows/bundle-deploy.yml` |
| `databricks-nightly-ingest.job.yml` | `answers-example-databricks.json` | `resources/nightly_ingest.job.yml` |
| `databricks-bundle-root.yml` | `answers-example-databricks.json` | `databricks.yml` at the repository root |

The only edit made to any of them is in the two markdown files: their relative links are
repointed at the sibling examples so they resolve from this directory. Each of those files
says so at the bottom and names the link the generator actually writes.

Things worth copying from them:

- The agent spec carries an `evidence` gate and anti-claims. A spec without both fails validation.
- The bundle-deploy workflow keeps credentials in `env` and pins the deploy job to an
  `environment`, so the protection rules on that environment are the approval gate. A prod
  deploy without one is a validation finding.
- The job resource declares `depends_on` with explicit `task_key` blocks, which is what makes
  the dependency graph checkable.
