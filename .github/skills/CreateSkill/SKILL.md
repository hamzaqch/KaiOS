---
name: create-skill
description: "The only sanctioned path for creating, editing, renaming or validating a skill. Owns the frontmatter schema, the ideal-state writing standard, the bundled-tool rules, and the validator that enforces all three. Hand-rolling a SKILL.md is how a skill ends up invisible to the model or triggering on everything. USE WHEN create a skill, new skill, make a skill, add a skill, build a skill, edit a skill, change a skill, rename a skill, add a tool to a skill, add a reference file, validate a skill, check a skill, skill frontmatter, skill description, skill is not triggering, skill triggers too often, my skill is ignored, skill schema. NOT FOR deciding which skills are worth building (use suggest-skills), authoring an agent file, writing path-scoped instructions, or shrinking an oversized doctrine file (use trim)."
argument-hint: "[create|edit|validate] <skill-name>"
---

# CreateSkill — the skill authoring contract

## What this produces

A skill directory that the harness discovers, the model routes to correctly, and the validator passes. Concretely: `.github/skills/<PascalName>/SKILL.md`, optional bundled `.py` tools and `references/*.md`, and a clean run of the validator.

## Done looks like

- `python .github/skills/CreateSkill/validate_skill.py .github/skills/<PascalName>` exits 0.
- The frontmatter carries a lowercase-hyphen `name` under 64 characters and a `description` under 1024 characters containing both `USE WHEN` and `NOT FOR`.
- The body states what the skill produces, what done looks like, and the contract for every bundled tool.
- Every bundled `.py` file runs `--help` with exit 0 and imports nothing outside the standard library.
- Invoking `/name` in chat loads it, and a neighbouring skill's `NOT FOR` points here rather than overlapping.

## USE WHEN

Any skill file is about to be written or changed. Including a one-line frontmatter tweak: the description is the routing layer, and editing it by hand is the most common way a working skill stops being found.

## NOT FOR

Choosing what to build (`suggest-skills`). Agent files, which are a different surface with different frontmatter. Path-scoped instruction files. Shrinking an over-long always-on file (`trim`).

## The schema

A skill is a directory under `.github/skills/` with a `SKILL.md` at its root.

```markdown
---
name: pr-review
description: "What it does. USE WHEN <triggers>. NOT FOR <exclusions>."
argument-hint: "<patch path or PR number>"
---
```

| Field | Rule |
|---|---|
| `name` | required. Lowercase letters, digits and single hyphens. 64 characters maximum. This is the `/slash` name, and it must be unique across every skill directory. |
| `description` | required. 1024 characters maximum. Must contain the literal `USE WHEN` followed by trigger phrases and the literal `NOT FOR` followed by exclusions. |
| `argument-hint` | optional. What follows the slash name, shown in the picker. |
| `user-invocable` | optional. Set false for a skill only other skills should reach. |
| `disable-model-invocation` | optional. Set true for a skill that must never auto-load. |

Two skills declaring the same `name` is a hard failure, not a warning: the slash command becomes ambiguous and auto-routing becomes a coin flip. Both the validator and the test suite fail on it and name both files, and the scaffolder refuses to create the second one. When a name you want is taken, the answer is almost always to extend the skill that has it.

Directory names are PascalCase; the `name` field is lowercase-hyphen. `CreateSkill` holds `create-skill`, `PrReview` holds `pr-review`. Once case and hyphens are dropped the two must agree, because that is how a reader finds the file for a slash command they saw in chat.

## The description is the router

Nothing else decides whether the skill gets used. The body is only read after the description already won.

- Lead with what the skill *produces*, in one clause. Not "helps with reviews" — "reviews a diff and returns a severity table".
- `USE WHEN` is a trigger list, not a sentence. Put the words a person would actually type, including the clumsy ones: "this is broken", "why is it slow", "check my ISA". Fifteen to thirty triggers is a healthy range.
- `NOT FOR` names the neighbouring skills by name. A description with no exclusions will steal invocations from its neighbours, and the fix is always in both descriptions at once.
- Never describe the skill's internals here. Nobody routes on implementation.

Two failure modes, both diagnosed from the description alone. **Not triggering**: the triggers are abstract nouns rather than the phrases people type. **Over-triggering**: the exclusions are missing, or the triggers are single common words like "check" or "build".

## The writing standard

Skills in KaiOS are ideal-state prompts, not runbooks. The difference is what happens when the situation does not match: a runbook breaks, a stated outcome adapts.

- State what done looks like, in outcomes a reader could check. That section is the skill's real contract.
- Give the model the constraints, the shape of the output, and the gotchas. Trust it with the ordering.
- Numbered steps are capped at eight. Past that, either the work is really a table, or the steps are compensating for an outcome that was never stated. The two exemptions carry a tag within the ten lines above the first item: `<!-- keep: tool-contract -->` for an exact invocation sequence, `<!-- keep: safety-gate -->` for a gate whose order is the safety property. Put it immediately above and there is nothing to remember.
- Prefer tables for anything comparative, prose for anything that requires judgment, bullets for parallel items.
- Never name an AI model. Roles only: max, high, medium, cross, third, research.
- No marketing words, no "powerful", no "seamlessly", no emoji headings.
- Write nothing personal: no names, no machine-specific paths, no reference to another system's internals.

## Bundled tools

A skill that needs determinism ships a Python file beside its `SKILL.md`, or calls `python -m kaios <group> <command>`. Prefer the CLI when the capability is general; bundle a tool when it is only useful inside this skill.

Every bundled tool obeys the same contract, and the validator checks most of it:

- Standard library only. Nothing from outside it, at all.
- `--help` exits 0 and describes the subcommands.
- A `--json` mode, because the caller is usually a model that needs to parse the result.
- `subprocess.run([...])` with an argument array. Never a joined command string, and never enable shell interpretation.
- Every file opened with an explicit `encoding="utf-8"`.
- Exit codes: 0 success, 1 the tool ran and found problems, 2 usage error or unreadable input. A tool whose absent dependency is expected exits 2 with a JSON error naming the install page.

Reference files go in `references/` and are reached by relative markdown link from `SKILL.md`. They exist so the main file stays short: a worked example, a question bank, a long table. The validator fails a broken relative link.

## Tool contracts

<!-- keep: tool-contract -->

| Command | Contract |
|---|---|
| `python .github/skills/CreateSkill/scaffold_skill.py --name x --description "… USE WHEN … NOT FOR …"` | writes `.github/skills/X/SKILL.md` with valid frontmatter and the section shape in place. `--argument-hint`, `--root`, `--dir-name`, `--force`, `--json`. Exits 1 rather than overwriting, accepting an invalid name, or taking a name another skill already declares. |
| `python .github/skills/CreateSkill/validate_skill.py <dir> [<dir> …]` | validates frontmatter, routing strings, step choreography, relative links and bundled-tool rules. Given several directories at once it also fails any pair that declares the same name. `--json` for machine output, `--strict` to fail on warnings. Exit 0 clean, 1 findings. |

Pass every skill directory in one invocation when checking the whole tree, because the name-collision check only sees the directories it is given: `validate_skill.py .github/skills/*/`.

Scaffold first, then fill, then validate. Writing the file by hand and validating afterwards works, but the scaffolder exists because the frontmatter rules are easy to half-remember and expensive to get wrong.

## Editing an existing skill

Read the whole `SKILL.md` before changing a line of it. Then:

- Changing behaviour means changing the `Done looks like` section too, or the two now disagree and the older one wins in the reader's head.
- Changing the routing means checking the neighbours. Add a trigger here, add the matching exclusion there, in the same change.
- Renaming means the directory, the `name` field, every `NOT FOR` in every sibling that referenced it, and any relative link. Grep for the old name before declaring it done.
- Validate afterwards, always. The validator is cheap and the failure mode it catches is silent.

## Constraints and gotchas

- A skill that duplicates another skill's job is worse than no skill: routing becomes a coin flip. Fold it into the existing one instead.
- Description length is a hard ceiling, not a target. A tight 400-character description routes better than a padded 1000-character one.
- The body can be long, but the reader is a model with other things to load. Push examples and question banks into `references/`.
- Do not put secrets, tokens or environment values in a skill. Skills are committed; environment is not.
- A skill is not a place for one-off instructions. If it will be used once, say it in chat.
