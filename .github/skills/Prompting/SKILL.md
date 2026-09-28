---
name: prompting
description: The standard for writing prompts, instruction files, agents, and skills in this system. Ideal-state prompting says a prompt states the outcome and how it will be checked, not the procedure, because a capable model finds a better procedure than the one you would have written. Covers the four keep-classes where exact sequence is preserved, the frontmatter contracts, and templates for each artifact kind. USE WHEN write a prompt, improve this prompt, write a skill, write an agent, write an instruction file, meta-prompting, prompt engineering, how should I word this, my skill does not trigger, the agent ignores part of the prompt, prompt template, system prompt. NOT FOR auditing an existing instruction set for bloat (use bitter-pill), producing the end content the prompt is meant to produce, or tuning model parameters.
argument-hint: "<what you are writing — prompt | skill | agent | instruction file>"
---

# Prompting

The output of this skill is always a prompt, never the thing the prompt produces.

## USE WHEN / NOT FOR

USE WHEN you are writing or repairing a prompt, skill, agent, or instruction file, or a capability does not trigger when it should.

NOT FOR auditing an existing instruction set for bloat, which is bitter-pill, or producing the content the prompt is meant to produce.

## What this produces

An artifact that another model can act on without asking what was meant.

## Done looks like

- The artifact states what done looks like in terms someone could check. If a reader cannot tell whether the output satisfied it, it is decoration.
- It says when to use the capability and when not to, so a router can pick correctly and so it does not fire on adjacent work.
- It names the output format the result must have, precisely enough that two runs produce comparable shapes.
- It contains no procedure a capable model would derive on its own, except inside a keep-class block.
- Bundled tools are described by contract — arguments, exit codes, output shape — never by narrating what to type when.
- It respects the frontmatter limits of the surface it targets, and it has been checked against them rather than assumed.

## Ideal-state prompting

State the destination and the test; let the model find the road.

| write this | not this |
|---|---|
| "The report has a findings table with severity per row and a remediation a builder could start today." | "First list the claims, then attack each one, then sort them, then write remediations." |
| "Falsifier — a claim marked done with no evidence line fails the gate." | "Remember to always check for evidence before marking anything done." |
| "The tool exits 0 on success, 1 on failure, 2 on usage." | "Run the tool and check whether it worked." |

Procedure prompts cap the model at the author's imagination and go stale the moment the environment changes. Outcome prompts improve on their own as models improve. The corollary is uncomfortable and correct: when a smarter model would make a rule unnecessary, the rule is costing you attention and buying nothing.

## The four keep-classes

Some sequences are not the model's to improve. Tag those blocks so audits and tests leave them alone. Any other numbered run longer than eight items is treated as choreography and flagged.

| tag | protects | example |
|---|---|---|
| `<!-- keep: tool-contract -->` | exact invocation, arguments, exit codes | a CLI usage block |
| `<!-- keep: safety-gate -->` | a confirmation or refusal sequence that must not be reordered | a destructive-command gate |
| `<!-- keep: output-schema -->` | a literal schema, frontmatter, or wire format | a JSON spec the tool parses |
| `<!-- keep: protocol-order -->` | steps whose order is externally required | an auth handshake, a migration order |

Put the tag on the line directly above the block, or at most a few lines above it.

## Output contract

A finished artifact from this skill carries, in this order: what it produces with done-criteria a reader can check, when to use it and when not to, the shape the result must have, the contract for any bundled tool, which role rung runs it, and the constraints that bite. Sections with nothing to say are deleted rather than padded. The artifact is delivered as the file it will live in, at the path its surface requires, not as prose describing what to write.

## Frontmatter contracts

| artifact | required frontmatter | limits |
|---|---|---|
| skill | `name`, `description` | `name` lowercase with hyphens, 64 characters or fewer; `description` 1024 characters or fewer and containing USE WHEN and NOT FOR |
| agent | `name`, `description`, `tools`, `model` | plus a `# kaios-role:` line as the first body line |
| instruction file | `applyTo` glob | keep the body under 4k characters, and scope it to the glob |

A description does double duty. It is documentation for a human and the routing signal for a model deciding whether to load the capability. Trigger phrases in USE WHEN should be the words a person would actually type, including the sloppy ones. NOT FOR exists to stop overtriggering, and the most useful entries name the neighbouring capability that should have fired instead.

## Templates

Working starting points for each artifact kind are in [templates](./references/templates.md) — skill, agent, instruction file, review prompt, judge prompt, and extraction prompt.

## Roles

Write and revise at the **max** role. Prompt wording is judgment about how another model will read ambiguity. Validate mechanical limits at the **medium** role or with a script, since character counts and frontmatter keys are not judgment. Have a **cross** role from a different vendor family read any prompt meant to run on several families, because wording that reads as obvious to one family can read as optional to another.

## Constraints and gotchas

- Write the done-criteria first. A prompt written body-first ends up describing a procedure, every time.
- One capability per artifact. A skill that does three things triggers on all three and does each of them worse.
- Do not stack emphasis. Capitals, bold, and repetition do not increase compliance; a checkable criterion does.
- Negative-only instructions underperform. Say what to do instead of the thing you are forbidding.
- Examples are expensive and powerful. One good contrast pair beats five similar samples.
- Test the trigger, not just the body. If the description does not contain the words a person would type, the best body in the world never loads.
