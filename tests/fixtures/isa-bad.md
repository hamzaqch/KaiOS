---
progress: 9/2
task: "Fixture that seeds one violation per check rule"
slug: bad
---

# Bad Fixture ISA

There is deliberately no Goal section, no phase in the frontmatter, and no
anti-claims block.

## Features

### F1 · Broken
Why: to seed every rule the checker enforces.

- [ ] ISC-1: this claim never says how it could be shown false.
- [ ] ISC-2: the first claim with this id. Falsifier: a probe.
- [ ] ISC-2: a duplicated id. Falsifier: a probe.
- [ ] ISC-7: waits on a claim that does not exist. Falsifier: a probe. (after: ISC-99)
- [ ] ISC-8: waits on itself. Falsifier: a probe. (after: ISC-8)
- [ ] ISC-9: the head of a cycle. Falsifier: a probe. (after: ISC-10)
- [ ] ISC-10: the tail of a cycle. Falsifier: a probe. (after: ISC-9)
- [x] ISC-11: closed with no evidence stub. Falsifier: a probe.
- [ ] ISC-3: an id that goes backwards. Falsifier: a probe.
