---
phase: climbing
progress: 1/4
task: "Fixture with features, edges, a tombstone, and evidence"
slug: good
started: 2026-01-01T00:00:00Z
updated: 2026-01-02T00:00:00Z
owners:
  - core
  - hooks
---

# Good Fixture ISA

## Problem

The parser has to survive its own format before anything else can rely on it.

## Goal

Prove the parser reads features, prerequisite edges, tombstones, and evidence stubs.

## Features

### F1 · Parsing
Why: the parser must read the format it defines.

- [x] ISC-1: frontmatter keys reach the caller. Falsifier: a declared key missing from the mapping. — evidence: tests/test_isa.py checks the mapping
- [ ] ISC-2: feature blocks group their claims. Falsifier: a claim with no feature id. (after: ISC-1)
- [ ] ISC-3: [DROPPED: superseded by ISC-4] the parser read pipe tables as claims.

### F2 · Edges
Why: prerequisites are what make a frontier meaningful.

- [ ] ISC-4: a claim with an unsettled prerequisite stays off the frontier. Falsifier: a blocked claim appears on it. (after: ISC-2, ISC-3)
- [ ] ISC-5: a tombstoned prerequisite does not block. Falsifier: this claim missing from the frontier. (after: ISC-3)

## Anti-claims

- A1: an anti-claim is never counted as an ISC.
- A2: the frontier never contains a tombstoned claim.

## Test Strategy

| ISC | probe | type |
|---|---|---|
| 1-5 | python -m unittest tests.test_isa | bash |

## Log

- 2026-01-01: fixture created.
