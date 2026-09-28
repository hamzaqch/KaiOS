---
version: 1.0.0
last_updated: 2026-09-28T00:00:00Z
convention: kaios-freshness-v1
---

# Self-healing — where a learning lives

> The routing table for where a new rule, preference, or piece of knowledge belongs. The constitution keeps the resident summary; this file carries the full table. Load it when deciding where to encode something learned, and when the system looks degraded and you need to know which surface to check.

## The principle

When the system fails — a rule was missed, a bad pattern recurred, a guard let something through — fix the system, not your notes. An operating system does not accumulate sticky notes about its own bugs; it patches itself. A fix encoded in the right surface is in effect for every future session with nothing to remember.

## Two diagnoses, one of which takes no patch

"The system failed" and "I failed" are different findings, and only the first one earns a change.

When a rule was already encoded correctly, already loaded, and simply not consulted, the correct remediation is **nothing**. Read it and do not repeat it. Building a gate to catch yourself disobeying doctrine you already hold adds machinery that a more careful reading makes pointless, and it makes the doctrine longer, which makes the next reading worse.

Watch for the reflex: being caught creates pressure to produce a visible artifact as proof of remediation, and a new hook or a new paragraph is the most legible artifact available. Resist it. A lapse is not a missing mechanism.

## The routing table

| What you are encoding | Where it goes |
|---|---|
| Doctrine, tone, an output contract, a convention that holds everywhere | `.github/copilot-instructions.md` |
| A rule that applies only to one language, one directory, or one file type | `.github/instructions/<topic>.instructions.md`, scoped by its `applyTo` glob |
| A checkable property of an artifact, or a gate on an irreversible act | a hook module under `.github/kaios/hooks/<event>/` |
| How to do a class of work — the capability, its done-criteria, its tools | that skill's `SKILL.md` under `.github/skills/<Name>/` |
| Which role a kind of work runs on, or a change to the model lineup | `.github/SYSTEM/CONFIG/models.json`, then `python -m kaios models apply` |
| State, claims, decisions and evidence for one piece of work | that work's `ISA.md` |
| A reusable fact about the codebase, the platform, or the domain | `MEMORY/KNOWLEDGE/<name>.md` with typed frontmatter |
| A dated failure narrative worth keeping as a signal | `MEMORY/LEARNING/INCIDENTS/INC-YYYYMMDD-<slug>.md` — the story lives there only, and rules cite the identifier |
| A self-critique about how a run went | a reflection line via `python -m kaios memory capture --kind reflection` |
| A proposal that was deliberately rejected and will be proposed again | `MEMORY/KNOWLEDGE/` with a clear title saying it was rejected and why |

## Choosing between doctrine and a hook

Both surfaces enforce, but they enforce different kinds of thing.

A **hook** is right when the rule is a property something either has or lacks, checkable without judgment — an ISA claim checked with no evidence stub, a command matching a destructive pattern, a write to a protected path, a secret-shaped string in a diff. It is also right when the act is irreversible and needs a human in the loop regardless of how good the model is.

**Doctrine** is right when the rule is about how to work: which tool to prefer, how to phrase an answer, when to ask, what order to do things in. Encoding that as a hook produces a gate that a competent reading of the doctrine already satisfies, and gates like that mostly fire on false positives until someone turns them off.

The test: *would a more capable model make this hook pointless?* If yes, the rule belongs in doctrine and the lapse belongs nowhere.

## Two invariants

**Never fix a failure by weakening the gate that caught it.** The gate firing is the system working. If a gate blocks something that should have passed, the fix is a more precise condition, never a lower bar, never a bypass flag, and never deleting the check. A gate that was loosened to let one thing through is a gate that will let the next thing through silently.

**Encode the fix in infrastructure, not in a memo.** A note that says "remember to check X" depends on someone remembering to read the note. The same content as a hook, an `applyTo` rule, or a claim in an ISA is in force whether anyone remembers or not. If a learning cannot be encoded anywhere in the table above, that is usually a sign it is not yet a rule — it is an observation, and it belongs in knowledge or nowhere.

## When the system looks broken

If context is missing, hooks seem to be misfiring, or the session is behaving as though doctrine did not load: read `.github/copilot-instructions.md` and this file before acting, then run `python -m kaios doctor`. Diagnose before changing anything. A degraded session that starts editing enforcement code makes the next session worse.
