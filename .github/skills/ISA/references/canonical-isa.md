---
version: 1.0.0
last_updated: 2026-09-28T00:00:00Z
convention: kaios-freshness-v1
---

# Canonical ISA — worked example

A complete, small ISA for a real-shaped task. Copy the shape, not the content. Frontmatter below is what `python -m kaios isa scaffold` writes; the body is what the engineer and Kai write together.

---

```markdown
---
phase: climbing
progress: 2/9
task: "Nightly invoice export to the finance share"
slug: invoice-export
started: 2026-09-20T09:15:00Z
updated: 2026-09-24T17:40:00Z
stated_goal: "finance keeps asking me for the invoice csv every morning, i want it to just be there by 7am and i want to know when it breaks"
---

# Invoice export — nightly, unattended, observable

## Problem

Finance asks for an invoice extract every weekday morning. Producing it is a manual
notebook run that takes about twenty minutes and is skipped whenever the person who
knows it is on leave. Two months of gaps exist in the shared folder. Nobody finds out
a run was missed until finance asks, which is on average four hours later.

## Vision

At 07:00 local the file is already in the share, named by date, with a row count that
matches the source. When it fails, the owning team hears about it before finance does,
with the failing step named. Nobody opens a notebook.

## Out of Scope

- Any change to how invoices are entered upstream.
- A UI. The deliverable is a file and an alert.
- Historical backfill of the two-month gap. Tracked separately.

## Language

- **Run** — one scheduled execution producing one dated file.
- **Row count parity** — the exported row count equals the source query count for the
  same window, exactly, not within tolerance.

## Principles

- Scheduled work that can fail silently is worse than manual work. Alerting ships with
  the first run, not after it.
- The export is idempotent: rerunning a date replaces that date's file and nothing else.

## Constraints

- Runs on the existing job runner. No new infrastructure.
- The share is reachable only from inside the network.
- Python standard library plus the platform SDK already installed on the runner.

## Dependencies

- Service principal with read on the invoice tables — exists, verified 2026-09-20.
- Write access to the finance share path — requested, pending, see Log.

## Goal

A scheduled nightly job writes a dated invoice CSV to the finance share by 07:00 on
weekdays, verifies row count parity against the source, and alerts the owning channel
with the failing step when any part of it does not hold.

## Claims

- [x] ISC-1: A single run writes `invoices-YYYY-MM-DD.csv` to the target path. Falsifier: run for a fixture date, file absent or misnamed. — evidence: tests/test_export.py::test_writes_dated_file
- [x] ISC-2: Rerunning the same date replaces that file and leaves other dates untouched. Falsifier: two runs produce two files, or a neighbouring date changes mtime. — evidence: tests/test_export.py::test_idempotent
- [ ] ISC-3: The export's row count equals the source query count for the same window. Falsifier: a seeded fixture where one line is dropped still reports parity. (after: ISC-1)
- [ ] ISC-4: A run that cannot reach the share exits non-zero and names the path. Falsifier: unreachable path exits 0, or the message omits the path. (after: ISC-1)
- [ ] ISC-5: Failure sends one alert to the owning channel naming the failing step. Falsifier: forced failure produces no alert, or an alert with no step name. (after: ISC-4)
- [ ] ISC-6: The job is scheduled 06:30 on weekdays and the schedule is in version control, not clicked into a UI. Falsifier: the schedule cannot be recreated from the repository alone.
- [ ] ISC-7: A run's log line records date, row count, duration and outcome as one JSON object. Falsifier: grep the log for a run with a missing field. (after: ISC-3)
- [ ] ISC-8: [DROPPED: finance confirmed CSV only, no Parquet] The export also writes Parquet.
- [ ] ISC-9: The runbook states how to rerun one date by hand and who owns the alert. Falsifier: a teammate cannot rerun yesterday from the runbook alone.

## Not yet specified

- Whether the alert should also fire on a run that succeeds but exports zero rows.
  Zero is legitimate on a holiday and pathological on a Tuesday. Needs a rule from finance.
- Retention on the share. No policy exists; not blocking the first run.

## Anti-claims

- A1: No run overwrites or deletes a file for a date it was not asked to produce.
  Probe: list the share before and after a run for a single date and diff.
- A2: No credential appears in the repository, the job definition, or a log line.
  Probe: grep the tree and the last 30 runs' logs for the secret's prefix.
- A3: A silent failure is impossible: no code path catches an exception and returns
  success. Probe: search for bare except and for handlers that do not re-raise or alert.

## Test Strategy

| ISC | Probe | Type |
|---|---|---|
| 1, 2, 3 | pytest against a seeded fixture database | unit |
| 4, 5 | forced-failure test with an unreachable path | unit |
| 6 | schedule file present and applied by the deploy command | command output |
| 7 | grep the emitted log for required keys | command output |
| 9 | a teammate follows the runbook cold | human |
| A1 | before and after listing of the share | command output |
| A2 | grep over tree and run logs | command output |
| A3 | search for exception handlers | code search |

## Decisions

- D1 (2026-09-20): CSV, not Parquet. Finance opens it in a spreadsheet. ISC-8 dropped.
- D2 (2026-09-21): Alert on failure only, not on success. A daily green alert would be
  muted within a week and then the red one would be muted with it.
- D3 (2026-09-23): Row count parity is exact, not approximate. An approximate check was
  tried first and passed while a join silently dropped 4 percent of lines. Dead end kept
  here on purpose so it is not retried.

## Log

- 2026-09-20: ISA scaffolded. Read access verified against the invoice tables.
- 2026-09-21: Share write access requested from platform. Not blocking: ISC-1 and ISC-2
  develop against a local temp path.
- 2026-09-23: Approximate parity check removed after it masked a dropped-join defect.
  See D3. ISC-3 tightened to exact.
- 2026-09-24: ISC-1 and ISC-2 closed on the fixture suite.

## Remaining Work

Row count parity (ISC-3) is next and unblocked. The alerting pair (ISC-4, ISC-5) needs
the owning channel name from the team. Share access is still pending and blocks the
first real run but blocks none of the current claims.
```

---

## What makes this one canonical

- The stated goal is verbatim, including its lowercase and its typo. Drift is measured against that string.
- Every claim names a probe. ISC-9's probe is a human following a runbook, which is a legitimate probe type as long as it is written down.
- The dead end in D3 is more valuable than the two decisions above it, because it stops the same wrong approach being tried again.
- The fog section holds a real open question with the reason it is open, rather than a placeholder.
- The dropped claim keeps its id, so D1's reference to ISC-8 still resolves.
- Closed claims carry a one-line evidence stub, not the test output.
