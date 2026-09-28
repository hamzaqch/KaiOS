---
version: 1.0.0
last_updated: 2026-09-28T00:00:00Z
convention: kaios-freshness-v1
---

# Philosophy — why KaiOS is shaped this way

> Load this when explaining KaiOS to someone, writing documentation about it, extending it, or arguing about whether a rule should exist.

## Intent engineering

The bottleneck in working with a capable model is not execution. It is direction. The model can write the code; what it cannot do is know what you actually meant, which constraints are real, what you would consider finished, and what you would consider a disaster. Every hour lost to an AI-assisted task is almost always lost to a gap between what was asked and what was understood.

**Intent engineering is the discipline of closing that gap structurally rather than conversationally.** It is prompting's *what* layer, made into infrastructure: capture what you are actually trying to achieve, carry that intent into every task automatically, and then verify the output against it. KaiOS is one implementation. The constitution carries standing intent — how you want work done. The project table and profile carry context — what you work on. The ISA carries per-task intent — what done means this time. Hooks carry the parts that must not depend on anyone remembering.

Verification is the second half of the same discipline, not a separate concern. Intent that cannot be checked is a wish. The reason KaiOS is built around falsifiable claims is that a claim with a probe is the only form of intent that can tell the difference between progress and motion.

The experiential target is **euphoric surprise**: the output you actually wanted, in the time it should have taken, at the cost it should have taken. That target covers the verifiable work (a migration, a pipeline, a fix) and the work that has to *land* (a design, a document, an explanation) with one frame, because both are a move from a current state to an ideal one.

## The ISA is a universal primitive with five identities

An Ideal State Artifact is one Markdown file per piece of work. Its power comes from being five things at once, in the same file, with no synchronisation problem between them.

1. **The specification.** What done means, as claims. Not a description of the work, and not a task list — a set of statements about the finished state that are either true or false.
2. **The test suite.** Every claim names the probe that would falsify it. The spec and the tests are the same document, so they cannot drift apart. `## Test Strategy` is the machine-readable form of that.
3. **The state of record.** For anything with a persistent identity, the ISA outlives every run. Between runs it says what the thing currently satisfies, each claim pointing at its evidence. "Add a feature" means "add claims that do not hold yet".
4. **The plan.** Claims carry optional ordering edges, so the set of claims that are open with no unmet blockers is the frontier — what can be worked right now, computed rather than re-derived by rereading everything.
5. **The handoff.** It is durable state that a fresh session, a different model, or a different engineer can resume from. Resume reads the artifact, never the conversation. This is what makes it safe to close a long session and start clean instead of pushing through a compaction.

One consequence worth naming: because the ISA is all five, keeping it current is not overhead beside the work. It *is* the work's record, its test plan, and its status report, and a run whose ISA never changed while the work taught it things has an out-of-date specification pretending to be finished.

## Hard-to-vary claims

Borrowed from the philosophy of explanation: a good explanation is **hard to vary** — every detail plays a functional role, so you cannot change a piece without breaking it. A bad explanation is easy to vary: you can swap its details freely because none of them does any work.

Claims are the same object. A hard-to-vary claim can be satisfied in essentially one way, and any weakening of the thing it describes would falsify it. An easy-to-vary claim can be satisfied by almost anything.

- Easy to vary: *the import job is reliable.*
- Hard to vary: *a malformed row fails that row only, writes it to the reject table with its error, and the job still exits zero.*

The operational test is the probe. **If you cannot name what would prove the claim false, it is not hard to vary** — which is exactly why every claim in an ISA carries a falsifier. Testability and hard-to-variability are the same property seen from two angles: a claim's hardness is precisely what a test would catch someone weakening.

Two corollaries that show up constantly in practice:

- **Universal claims beat example claims.** "This parser round-trips every record in the fixture set" is one quantifier stronger than "this parser handles the sample I tried". When a property can be stated over a domain, state it over the domain.
- **Evidence is part of the deliverable.** A finished run produces the change *and* the evidence that the change satisfies the claims. Either one alone is half a delivery.

## Ideal-state prompting

The same epistemology governs how KaiOS prompts itself. A skill body, an agent brief, a delegated task — each is a description of a goal, and the good version is hard to vary: it names *what* done looks like as testable outcomes, names the constraints that bound the solution space, and hands over good tools. It does not name *how*.

The moment a prompt starts choreographing reasoning — "first analyse the inputs, then consider the edge cases, then form a hypothesis, then decide" — it has stopped describing the goal and started scripting the worker. That fails twice. It caps the model at the intelligence of whoever wrote the procedure, and it rots: every capability gain in the underlying model makes more of the choreography redundant, so a procedure written for last year's model actively degrades this year's.

Ideal-state prompting is not vaguer than procedural prompting. It is **more precise**, because the specificity moves to where it belongs — the outcome. "Produce a threat model that enumerates every trust boundary and names a concrete attack against each" is a tighter instruction than five steps on how to think about threat modelling, and it survives a model upgrade because it constrains the deliverable rather than the reasoning.

### The four keep-classes

Four kinds of *how* are legitimate and survive the cut, because a more capable model does not make them unnecessary. They encode facts that capability alone cannot derive.

- **Safety gates.** Confirmation requirements, destructive-operation guards, approval boundaries, the rule that a production deploy always asks. These bind regardless of intelligence, because they are about authority and consequence rather than competence.
- **Verified gotchas.** A documented non-obvious failure the model would otherwise walk into: a command whose success exit code lies, a config key that is silently ignored when misspelled, an API that returns 200 with an error body. These are empirical facts about the world. A gotcha needs provenance — a dated incident, a failing test, a reproduction. Without provenance it is somebody's preferred procedure wearing a better label, and it gets cut. This one bar is what keeps the taxonomy from collapsing into permissiveness.
- **Tool contracts.** Exact command syntax, parameter names, file paths, argument order, the shape of a JSON payload. A more capable model still cannot guess an undocumented flag.
- **Output format contracts.** The required shape of the deliverable — a schema, a table's column order, the response format. The model stays free on how and bound on the final form.

Two clarifications keep this honest, because the keep-classes are exactly what a defender of bad methodology will hide behind. First, **the cut governs imperative process, not declarative facts** — environment facts, domain invariants, API shapes, and worked examples are declarative and stay. Stripping domain knowledge as "methodology" is over-cutting, and the failure mode is symmetric with over-prompting. Second, **the Algorithm is not exempt**: its gates, artifacts and records are machinery and survive, but anything inside it that scripts cognition is ordinary choreography and gets cut like anywhere else.

### The test

For any procedural line anywhere in KaiOS, ask: **would a smarter model make this line unnecessary?**

Yes means it is scaffolding. Cut it. No means it is one of the four keep-classes, and it stays. Apply the test to this file too.
