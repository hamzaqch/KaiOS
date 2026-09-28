# Data Quality Review

> Check a dataset or pipeline for the failures that produce confidently wrong numbers.

## Done means
- Row counts and their expected range are stated, per partition or per day, not just in total.
- Every key is checked for uniqueness and every join for fan-out, with the actual measured multiplier.
- Nulls are characterised as expected or unexpected per column, against a stated rule.
- Time handling is checked — timezone, late arrivals, the boundary between event time and load time.
- Duplicates, silent type coercions, and truncated strings are looked for explicitly.
- Each finding says what a downstream consumer would compute incorrectly because of it.

## Output contract
```
## Dataset and scope
## Volume
| partition | rows | expected | verdict |
## Keys and joins
| relation | expected cardinality | measured | fan-out risk |
## Column checks
| column | type | null rate | rule | verdict |
## Time
## Findings
| # | finding | downstream consequence | check to add |
## Monitors to add
```

## Gotchas
A pipeline that runs green and produces wrong numbers is the normal failure, so check outputs, not job status. Compare against an independent count where one exists. Late-arriving data makes yesterday's correct total wrong today, and that is a design question, not a bug.
