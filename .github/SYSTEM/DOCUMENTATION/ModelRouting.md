---
version: 1.0.0
last_updated: 2026-09-28T00:00:00Z
convention: kaios-freshness-v1
---

# Model routing

> How KaiOS uses several vendors' models deliberately instead of accidentally. **No model name appears anywhere in this document, or in any other doctrine prose.** Model names live in exactly one file — `.github/SYSTEM/CONFIG/models.json` — because a name written into prose is a name that goes stale the next time a lineup changes, and stale prose is worse than no prose.

## The situation

Copilot in VS Code exposes models from three vendor families: **Anthropic**, **OpenAI**, and **Google**. Which specific models are available depends on what an organisation has enabled, and that list changes without warning.

Treating them as interchangeable wastes the one real advantage of having three: they are trained differently, so they are wrong differently. A weakness one family shares across its whole lineup is a weakness a different family often does not have. That is worth more than any individual capability difference between them.

So KaiOS never picks a model. It picks a **role**, and the registry resolves the role to whatever is currently available and preferred.

## The six roles

| Role | Purpose | Typical work |
|---|---|---|
| `max` | judgment | planning, design, scoping, review, audits, anything touching KaiOS itself, anything where being wrong is expensive |
| `high` | execution | building work that is already scoped and whose done-criteria are written down |
| `medium` | trivial execution | formatting, mechanical edits, renames, summarising something already understood |
| `cross` | a second look | reviewing or auditing work built by a *different* vendor family |
| `third` | a third opinion, and long context | breaking a tie, reading a very large document set in one pass |
| `research` | reading | web research, large documentation sweeps, gathering before deciding |

Two things this table is not. It is not an effort budget — how much to spend on a task is discovered from the work, and only *which rung* is written down. And it is not a quality ranking of vendors: `max`, `cross` and `third` are deliberately seated in different families, so a family in one role is not being demoted from another.

## Which vendor family does what

The assignment is by disposition, not by score, and it is a default the registry can change per organisation.

- **The `max` seat** goes to the family whose lineup is strongest at long-horizon reasoning over a codebase and at holding a specification in mind while building against it. This is the seat that plans, reviews, and does meta work on KaiOS.
- **The `cross` seat** is always a *different* family from whichever one built the artifact under review. Its job is to find what the builder's family cannot see about itself.
- **The `third` seat** goes to the remaining family, and it doubles as the long-context reader because that is where the largest usable context windows have tended to be. It breaks ties between the other two and takes the jobs where the whole input has to be in the window at once.
- **The `research` seat** goes to whichever family is best at grounded retrieval and summarising a large external corpus faithfully.
- **`high` and `medium`** are cost-and-latency seats. They take execution work whose correctness is already pinned by claims and probes, so the expensive judgment has already happened upstream. Any family can hold them.

## The one hard rule

**A second look is always a different vendor family from the builder.**

A model reviewing output from its own family shares that family's training, its habits, and its blind spots. It also tends to find the choices familiar and therefore reasonable, which is the opposite of what a review is for. Worse, a delegate that inherited the build context is not a reviewer at all — it defends its own work.

So the Auditor role never audits a build from its own family. When the builder ran in family A, the audit runs in family B or C. If only one family is available in an organisation, the honest outcome is "no independent second look was available", recorded in the ISA Log as a skip with a reason — not a same-family review relabelled as independent.

The corollary for briefs: a reviewer gets the goal, the claims, and the artifact. It never gets the build plan or the conclusion it is expected to reach. A verifier told what a pass looks like reasons its way to that pass.

## The Council

The Council skill exists to make the multi-vendor situation useful on questions that have no probe — an architecture choice, a tradeoff, a "which of these three approaches" question.

It seats **one agent per vendor family present in the registry**, briefs each on the same question with the same context, and lets them disagree in the open across rounds. One seat per family is the whole point: three agents from one family produce three versions of the same answer, confidently, and that reads like consensus when it is only correlation.

Rules the Council runs by:

- Same brief to every seat, issued before any seat has seen another's answer.
- Disagreement is the output. A round where all seats agree immediately is either an easy question or a badly framed one.
- Contradictions get surfaced to you, not resolved silently by whichever seat spoke last.
- Its output is a recommendation with the dissent attached, never a vote count.

## Downshifting for execution

The main session runs the `max` rung. Design, planning and judgment happen there, inline, with no negotiation about which rung to use.

The only rung move that gets elected is the **downshift**: once work is scoped and its claims are written, the execution leg can be dispatched to a `high` agent, or to `medium` when the execution is genuinely mechanical. What makes that safe is that the claims and their probes already exist — the executor is climbing a hill someone else surveyed, and its output is checked against falsifiers rather than trusted.

Escalate back up the moment an execution leg hits something that needs judgment: a claim that turns out to be wrong, a constraint nobody wrote down, an ambiguity in the goal. A `high` agent quietly reinterpreting a claim is worse than one that stops and reports.

## Homogeneous fan-outs correlate

Parallel workers sharing one family and one prompt scaffold fail the same way at the same place, which makes the failure invisible — every worker agrees, so nothing looks wrong.

Past roughly four workers on open-ended work, vary something across them: the family, the lens they are asked to take, or the scaffold of the brief. Mechanical sweeps over disjoint inputs are exempt, because there is no judgment to correlate.

## The registry

`.github/SYSTEM/CONFIG/models.json` maps each role to a prioritised list of model identifiers. First available wins, so a list is both a preference and a fallback chain.

```json
{
  "roles": {
    "max": { "purpose": "judgment, planning, review, audits, meta work", "models": ["…", "…"] }
  }
}
```

Every agent file carries `# kaios-role: <role>` as its first body line. That line is the source of truth for which seat the agent holds.

| Command | Does |
|---|---|
| `python -m kaios models show` | print the registry with which roles resolve to what |
| `python -m kaios models set <role> <a,b,c>` | replace a role's prioritised list |
| `python -m kaios models apply` | rewrite the `model:` frontmatter of every agent file from the registry |

`models apply` is what keeps the rule enforceable. Agent frontmatter is *generated* from the registry rather than maintained by hand, so changing the lineup is a one-file edit plus one command, and no prose anywhere has to be found and updated.

Setup asks which models your organisation has enabled and writes your answers into your own copy of the registry. Nothing in the doctrine layer changes when that answer changes.

## When routing is unavailable

Every role degrades to "whatever the session is already running on", and KaiOS keeps working. A single-model organisation loses the cross-family second look and the Council's independence, and both losses are recorded rather than papered over. Nothing else in the system depends on having three families.
