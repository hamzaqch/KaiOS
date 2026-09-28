---
name: sql-notebooks
description: Rules for SQL files and notebooks — parameterize every value, never drop or overwrite without asking, Delta practices that keep a table recoverable.
applyTo: "**/*.sql, **/*.ipynb"
version: 1.0.0
last_updated: 2026-09-28T00:00:00Z
convention: kaios-freshness-v1
---

# SQL and notebooks

## Parameterize every value

Never build a query by interpolating a value into the string. Not for a date, not for an identifier someone typed, not for "just this once in a notebook".

```python
spark.sql("SELECT * FROM events WHERE day = :day", args={"day": day})
```

A notebook is the worst place to make this exception, because cells get copied into jobs. When the varying part is genuinely an identifier that cannot be a bind parameter, validate it against an allow-list of known names first. An identifier from outside the notebook is never trusted.

## Destructive statements ask first

`DROP`, `TRUNCATE`, `DELETE` without a `WHERE`, `INSERT OVERWRITE`, `REPLACE TABLE`, `ALTER TABLE ... DROP COLUMN`, and anything writing to a production catalog: state what it will affect and wait for a yes. Every time, including inside an approved run.

First know three things: how many rows it touches, whether time travel reaches far enough back to recover, and what reads from it downstream. "It is only a staging table" precedes incidents.

`DestructiveCommandGuard` denies the unqualified forms. It is a backstop, not a substitute for thinking.

## Reads before writes

Any statement that changes data gets a matching `SELECT` first, with the same predicate, whose row count you actually look at. A `DELETE` whose `WHERE` matched ten million rows instead of ten is indistinguishable from a correct one until afterward.

After the write, verify with a `SELECT` — the row count, a sampled row, the aggregate that should have changed. A statement that reported success is not evidence that the data is right.

## Delta practices

- **`MERGE` over delete-then-insert.** Delete-then-insert leaves a window where the table is wrong.
- **`MERGE` needs a unique key on the source.** Duplicates on the match key fail, or worse, update the same target row twice. Deduplicate in the same statement and assert the count.
- **Schema evolution is explicit.** `mergeSchema` on the one write that needs it, never as a default — a default that accepts any schema accepts a broken upstream silently.
- **Partition on what is filtered, not on what is unique.** A high-cardinality partition column produces a directory per row.
- **`VACUUM` shortens the recovery window.** Know the retention first, and never shorten it to reclaim space during an incident.
- **Time travel is the undo.** `DESCRIBE HISTORY` before a risky change and note the version. That number is the difference between a five-minute recovery and a restore from backup.
- **Idempotent writes.** A rerun after a partial failure must not double-write. Deterministic key plus `MERGE`, or replace a whole partition, never append blindly.

## Notebooks

- Cells run top to bottom on a fresh kernel, or the notebook is not reproducible. No cell depends on a variable defined in a cell below it or in a previous session.
- Parameters at the top, in one cell, named and with defaults. Never a value edited in place halfway down.
- No credentials in a cell, ever — not in a string, not in a comment, not in cleared output. Reference a secret scope or an environment variable name.
- Clear output before committing. Committed output leaks data, inflates diffs, and makes review useless.
- A notebook that became a job belongs in a `.py` file. Notebooks are for exploring; jobs are for running.

## Claims about data

A claim about data closes on a `SELECT` that returned rows, run against the real table after the change. Not on the write reporting success, not on the count the code intended to write, and not on a local test over a fixture — a fixture cannot reproduce a catalog.
