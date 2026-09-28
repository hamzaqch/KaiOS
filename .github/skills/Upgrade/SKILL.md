---
name: upgrade
description: "Improves KaiOS itself from two sources: what the tooling has newly made possible, read from the editor's and the coding agent's own release notes, and what this team has actually hit, read from the memory digest. Produces concrete diffs against real files, each filtered against current state so nothing already done or already rejected gets proposed again. USE WHEN upgrade, upgrade KaiOS, improve the system, new features, release notes, changelog, what is new in the editor, new agent capability, can we use the new hooks, mine the reflections, what have we learned, system improvements, is there a better way to do this now, modernise the setup, the harness feels dated. NOT FOR upgrading a project's dependencies, editing one skill (use create-skill), shrinking a doctrine file (use trim), or researching a topic unrelated to the harness (use research)."
argument-hint: "[releases|reflections|both]"
---

# Upgrade — make the harness better than last month

## What this produces

A short list of proposed changes to KaiOS, each one a concrete diff against a named file, with the reason it is worth doing and the evidence that it is not already done. Proposals, not applied changes: each one lands through the skill that owns the surface.

## Done looks like

- Every proposal names the file it changes and what the change is, specifically enough to apply.
- Every proposal states its source: a release note with its version, or a memory record with its date.
- Every proposal was checked against the current repository and is not already implemented.
- Anything previously considered and rejected is listed as such, with the earlier reason, rather than proposed again.
- The list is ranked, and the bottom of it is honest about being optional.

## USE WHEN

The tooling has shipped something new, a quarter has passed, the same friction keeps appearing in reflections, or someone asks whether the harness is making use of what is available.

## NOT FOR

A project's own dependencies. Editing a single skill (`create-skill`). Trimming (`trim`). General research (`research`).

## Two sources, in this order

**Reflections first.** What this team actually hit beats what a vendor announced. Read the digest and look for repetition: the same correction three times, the same missing tool, the same manual step. A friction that appeared once is noise; one that appeared four times is a specification.

```
python -m kaios memory digest --since <a month ago>
python -m kaios memory search <the friction you suspect>
```

Read past the individual records for the pattern. The useful finding is rarely "this broke"; it is "this broke because the system has no place to put that kind of rule".

**Release notes second.** Fetch the editor's release notes and the coding agent's changelog for the versions released since the last upgrade pass. Read for capability, not for features: a new hook event, a new frontmatter field, a new way to scope instructions, a change to how skills are discovered, a new model role available in the picker. Most entries in a release note change nothing here, and saying so is a valid outcome.

When fetching, name the version you read in the proposal. A proposal citing "recent release notes" cannot be checked, and six months later nobody knows whether it was based on something real.

## Filter against current state

This is where the value is, and it is the step that gets skipped. Every candidate gets three checks before it becomes a proposal:

- **Already done?** Grep the repository. A proposal to add something that exists is worse than no proposal, because it makes the whole list untrustworthy.
- **Already rejected?** Search memory and the ISA's Decisions for the idea. A decision with a reason stands until the reason changes; if the reason has changed, say which part changed and propose it as a revisit, not as a new idea.
- **Would it earn its place?** A capability is not a reason to use it. Name the friction it removes, from the reflections or from a concrete failure. A proposal whose justification is that the feature exists goes at the bottom of the list, marked optional.

## Proposal shape

One block each, ranked, with the weakest ones still included and honestly labelled.

```
### Scope path-scoped rules to the notebook directory
Source: editor release notes 1.9x, instructions applyTo now supports negation.
Friction: three reflections in six weeks about notebook rules firing on plain .py files.
Change: .github/instructions/notebooks.instructions.md — narrow applyTo, add the negation.
Checked: current file uses a single glob; grep shows no negation anywhere in the tree.
Cost: one file, no behaviour change outside notebooks.
```

Ranked by friction removed, not by how interesting the capability is. A boring change that stops a recurring correction beats a clever one nobody asked for.

## Applying

Nothing is applied by this skill. Each accepted proposal goes to the surface that owns it: skill changes through `create-skill`, always-on file size through `trim`, doctrine and hook changes as ordinary work under `algorithm` with an ISA. Record the decision either way, so the next upgrade pass can see what was rejected and why.

## Tool contracts

<!-- keep: tool-contract -->

| Command | Contract |
|---|---|
| `python -m kaios memory digest [--since ISO]` | what recent runs learned, grouped by kind |
| `python -m kaios memory search Q` | has this friction appeared before |
| `python -m kaios ledger log` | what was already changed, and when |
| `python -m kaios ledger version` | the current version, for the proposal's baseline |
| `python -m kaios integrity docs` | whether a proposed doc change would break a cross-reference |

Use the editor's fetch capability for release notes. Quote the version and the specific entry; a paraphrase of a changelog is not a source.

## Constraints and gotchas

- Do not propose more than about six changes. A long list is a list nobody acts on, and the ranking is the product.
- Never propose a change to a file you have not read in its current state. The most common wrong proposal is one that argues for something already there.
- A new model appearing in the picker is a registry change, not a prose change. It goes in the model registry and propagates; no doctrine file should ever name a model.
- Resist proposing more instructions. The default answer to friction is usually a better tool or a deleted rule, not another paragraph in an always-on file.
- Record the pass itself, even when it proposes nothing. "Read the notes for versions X through Y, nothing applies" is a useful record that stops the next pass re-reading them.
