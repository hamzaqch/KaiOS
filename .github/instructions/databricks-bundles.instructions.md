---
name: databricks-bundles
description: Rules for bundle configuration — validate before every deploy, production behind an explicit ask, targets that cannot be confused for each other.
applyTo: "**/databricks.yml, **/resources/**"
version: 1.0.0
last_updated: 2026-09-28T00:00:00Z
convention: kaios-freshness-v1
---

# Databricks bundles

## Validate before every deploy

```
databricks bundle validate -t <target>
```

Always, before any deploy, including one that is "just a config change". It catches a bad reference, a missing variable, and a target resolving to a workspace nobody meant. It is the only step between a typo and a deploy.

Read the validation output rather than the exit code alone. A warning about an unresolved variable is the shape of a deploy that silently used a default.

## Production asks, every time

```
databricks bundle deploy -t prod
```

This is never run without an explicit yes, even inside an approved run, even when the same change already deployed to development, even when it is a rollback. State what will change — which jobs, which schedules, which permissions, which cluster definitions — and wait.

`databricks bundle destroy` against any shared target is in the same class, and so is any change to a target's `run_as` or permissions block.

`DestructiveCommandGuard` asks on a production deploy. It is a backstop, not the decision.

## See the diff before deploying

`bundle deploy` shows what it will create, update, and delete. Read the delete list. A resource disappearing from configuration is a resource that gets deleted from the workspace, and a job deleted this way takes its run history with it.

A renamed resource is a delete plus a create. When the history matters, plan the migration rather than letting the diff do it.

## Targets

- One target per environment, named so they cannot be confused: `dev`, `staging`, `prod`. Never a target whose name does not say which environment it is.
- Every target sets `workspace.host` explicitly. A target that inherits a host from an ambient profile deploys wherever the machine happens to be pointed.
- `mode: development` on developer targets. It prefixes resources per user and pauses schedules, which is what stops a developer deploy from competing with production for the same job name.
- `mode: production` on the production target, with `run_as` set to a service principal rather than a person. A job running as a human breaks when that human's access changes.
- Never a default target that is production. The safe default is the one that does the least damage when someone forgets the flag.

## Configuration shape

- Variables for everything that differs between targets: paths, catalogs, schemas, cluster sizes, notification addresses. A value hard-coded in a shared file is a value that will be wrong in one environment.
- Resources split into `resources/*.yml` by resource. One large file is a merge conflict waiting to happen.
- Pin library versions. An unpinned dependency lets a redeploy change behaviour with no config change.
- No secret values in the bundle. Reference a secret scope — a committed secret stays committed.
- Schedules paused in non-production targets. An unpaused development schedule quietly burns compute.

## Verifying a deploy

A deploy claim closes on evidence from the workspace, not on the deploy command's exit code:

- `databricks bundle summary -t <target>` showing the resources as deployed
- for a job, the job definition read back, and a run that actually succeeded
- for a schedule, the next scheduled time read back from the workspace

"The deploy succeeded" is not "the job runs". Those are two claims and each needs its own probe.

## CLI calls from code

Argument arrays, never a shell string, and never `shell=True`. Check the return code explicitly. When the CLI is absent, exit with a clear message saying so rather than a traceback — every Databricks integration in this system is optional, and absent is a normal state.
