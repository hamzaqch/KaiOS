---
name: databricks
description: "Optional domain skill for a Databricks workspace, driven through the CLI with argument arrays and two hard approval gates. Checks auth, lists a workspace path, lists and triggers jobs, validates and deploys asset bundles, runs a parameterised SQL statement through the statement API, and exports a notebook. Refuses a production bundle deploy and any destructive statement without explicit human approval. USE WHEN databricks, workspace, unity catalog, delta table, asset bundle, bundle validate, bundle deploy, dbx job, job run, run the job, trigger the job, sql warehouse, run a query against the warehouse, export a notebook, notebook, who am I on the workspace, which profile, catalog schema table, is the table there, why did the job fail. NOT FOR writing the transformation logic itself (that is ordinary work under algorithm), any other cloud platform, or local data files."
argument-hint: "[auth-check|workspace-ls|jobs-list|jobs-run|bundle-validate|bundle-deploy|sql-query|notebook-export]"
---

# Databricks — the one domain tool, wrapped safely

## What this produces

Verified answers about a real workspace: who you are authenticated as, what is at a path, which jobs exist and what a run did, whether a bundle is valid, and what a query returns. Every call goes through the CLI as an argument array, and every result comes back as JSON.

This skill is entirely optional. When the CLI is not installed, every subcommand exits 2 with the install link and nothing else in KaiOS changes.

## Done looks like

- `auth-check` was run before anything else, and its output names the workspace and identity actually in use.
- Every claim about the workspace is closed on the platform's own output, not on a local file that describes it.
- A production deploy happened only after a human approved it in this conversation, and the approval is recorded.
- Any destructive statement was named, approved, and preceded by a count of what it would affect.
- The profile in use is stated in the response, because the same command against the wrong profile is the most expensive mistake available.

## USE WHEN

Anything about the workspace: authentication, paths, jobs, bundles, queries, notebooks.

## NOT FOR

Writing the transformation logic, which is ordinary work under `algorithm`. Other platforms. Local data files.

## Which subcommand

| Question | Subcommand |
|---|---|
| Am I authenticated, and as whom, against which workspace | `auth-check` |
| What is at this workspace path | `workspace-ls <path>` |
| Which jobs exist, what are their ids | `jobs-list` |
| Run this job now | `jobs-run <job-id> [--param k=v]` |
| Is this bundle well-formed, what would it deploy | `bundle-validate [--target T]` |
| Deploy the bundle | `bundle-deploy --target T` |
| What does this query return | `sql-query --warehouse-id W --sql "…"` |
| Get this notebook's source locally | `notebook-export <path> [--file local.py]` |

Start with `auth-check`, always, and read its output rather than assuming. Two profiles pointing at two workspaces is the normal state of a working setup, and every other command in this table is harmless against the right workspace and expensive against the wrong one.

## The gates

<!-- keep: safety-gate -->

Two operations refuse to run without an explicit `--approved` flag. Both return `{"requires_approval": true}` and exit 3.

1. **A bundle deploy whose target looks like production.** Any target matching `prod` triggers it. Validate first, show the human what the deploy would change, get a yes in words, then rerun with `--approved`.
2. **A SQL statement that drops, truncates, replaces, deletes or vacuums.** Before asking for approval, run the read-only version of the same question: count the rows the statement would affect, and name the table's full three-part path. An approval given without that count is not an informed approval.

Never pass `--approved` on the strength of an earlier instruction, a similar approval, or your own judgement that the target is safe. The flag represents a human saying yes to this specific operation now. An approval for the dev target is not an approval for prod, and an approval last hour is not an approval for a second run.

Exit 3 is a distinct code so a caller can tell "needs a human" apart from "failed".

## SQL against Unity Catalog and Delta

**Parameterise, always.** Use `:name` placeholders in the statement and `--param name=value`, never string interpolation. This is not only about injection: an interpolated date that arrives as the wrong type produces a query that runs, returns rows, and answers a different question than the one asked.

**Three-part names, always.** `catalog.schema.table`. A two-part name resolves against whatever the session's current catalog happens to be, which differs between your CLI profile, a job's cluster, and a notebook. The same query then returns different data in each place, and nothing errors.

**Grain before aggregates.** Confirm what one row means before summing anything. A table named for one entity holding one row per child entity is the single most common cause of a number that is confidently wrong: a join fans out, the total inflates, and nothing fails.

**Delta reads are snapshots.** A query sees the table version at the moment it started. Two queries a second apart can legitimately disagree, and a pipeline that writes between them will make them disagree. When a count has to match another count, get both from one statement or name the version.

**Time travel is the undo, and it is not infinite.** `VERSION AS OF` and `TIMESTAMP AS OF` can recover a table after a bad write, bounded by retention, and `VACUUM` ends that possibility permanently. That is why vacuum sits behind the approval gate with the drops.

**Permissions are not the same as existence.** An empty result can mean no rows or no grant. Before reporting that something is absent, confirm the probe can see a row you know is there.

## Jobs and bundles

A job's configuration in the workspace and the bundle in the repository are two different things, and they drift. The bundle is the source of truth only where it is actually deployed; a job edited in the interface will be silently reverted by the next deploy, which is usually correct and occasionally destroys someone's fix.

- `bundle-validate` before every deploy, including to dev. It is fast and it catches the whole class of errors that otherwise surface as a failed deploy halfway through.
- A triggered run returns a run id, not a result. The trigger succeeding is not the job succeeding: fetch the run's status before claiming anything about the outcome.
- When a job fails, read the run's own error output rather than reasoning from the notebook source. The failure is frequently in the cluster, a library version, or a permission, and the source looks fine.

## Tool contracts

<!-- keep: tool-contract -->

| Command | Contract |
|---|---|
| `python .github/skills/Databricks/databricks_tool.py <subcommand> [--profile P] [--json] [--timeout S]` | every subcommand. `--profile` passes through to the CLI, `--json` emits the structured result, `--timeout` bounds the call. |
| `… auth-check` | identity and workspace for the active profile |
| `… workspace-ls <path> [--absolute]` | one path's contents |
| `… jobs-list [--limit N]` | jobs with their ids |
| `… jobs-run <job-id> [--param k=v]` | triggers a run, returns the run id |
| `… bundle-validate [--target T]` | validates the bundle in the working directory |
| `… bundle-deploy --target T [--approved] [--force-lock]` | deploys. Exit 3 without `--approved` when the target looks like production |
| `… sql-query --warehouse-id W --sql "…" [--param n=v] [--catalog C] [--schema S] [--approved]` | statement API call. Exit 3 without `--approved` for destructive statements |
| `… notebook-export <path> [--format SOURCE\|HTML\|JUPYTER\|DBC\|AUTO] [--file local]` | exports a notebook |

Exit codes: 0 succeeded, 1 the CLI returned a failure, 2 the CLI is absent or usage was wrong, 3 approval required. Every invocation is `subprocess.run` with an argument list, so a path containing a space is one argument and cannot become two.

## Constraints and gotchas

- The profile is authentication and credentials are managed by the CLI. KaiOS stores the profile *name* and never a token, a host, or a secret.
- Authentication is interactive. When `auth-check` fails, the fix is for the person at the keyboard to run the login command in their own terminal; do not attempt it from here.
- A long query will hit the wait timeout and return a statement id rather than rows. That is a pending result, not a failure: poll it, and do not report the empty payload as an answer.
- Never report a row count from a `LIMIT`ed query as the table's count.
- Workspace paths are case sensitive and a missing path lists as an error rather than as empty. Read the error.
- Do not use this skill to explore a production workspace casually. Every listing is cheap, but a query against a large table is not, and a triggered job is not reversible.
