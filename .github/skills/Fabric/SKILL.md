---
name: fabric
description: A library of reusable analysis patterns, each one an ideal-state prompt with its own done-criteria and output contract, for recurring work like extracting wisdom from a long source, analyzing claims, reviewing code or an API, threat modelling, writing an architecture decision record, drafting a pull request description, explaining an error, or reviewing data quality. Pick a pattern, apply it to the input, return its contracted shape. USE WHEN fabric, run a pattern, apply a pattern, which pattern fits, extract wisdom, analyze claims, improve this writing, review this code, threat model, summarize this, make a mermaid diagram, explain this code, explain this error, write tests, rate this, write an ADR, draft a PR description, clean up meeting notes, refactor plan, api review, data quality check. NOT FOR one-off analysis no pattern covers (just do the work), writing new patterns as skills (use create-skill), or adversarial attack on a plan (use red-team).
argument-hint: "<pattern-name> <input path, url, or text>"
---

# Fabric

Twenty patterns for work that recurs. Each is a prompt with done-criteria, so the output is comparable run to run.

## USE WHEN / NOT FOR

USE WHEN the work is a recurring analysis shape one of the patterns already covers, and you want output comparable to last time.

NOT FOR one-off analysis no pattern covers, where doing the work directly is better, or writing a new pattern as a skill, which is create-skill.

## What this produces

The named pattern's contracted output, applied to real input.

## Done looks like

- A pattern was chosen and named in the output. When none fits, say so and do the work directly rather than bending a pattern to shape.
- The pattern's file was read before it was applied. Applying a pattern from its name alone loses the done-criteria, which is the only part that makes the output reliable.
- The output has the headings and table columns the pattern specifies. Deviations are stated and justified.
- The input was actually read in full. Patterns applied to a snippet produce findings about the snippet.
- The pattern's own gotchas section was checked against the result before returning it.

## Patterns

| pattern | what it does |
|---|---|
| [extract-wisdom](./references/patterns/extract-wisdom.md) | dense ideas, insights, quotes, and actions from a long source |
| [extract-ideas](./references/patterns/extract-ideas.md) | ideas only, deduplicated, for reuse elsewhere |
| [analyze-claims](./references/patterns/analyze-claims.md) | separate assertions from support, rate each on evidence |
| [summarize](./references/patterns/summarize.md) | compress so a reader who never opens the source can act |
| [rate-content](./references/patterns/rate-content.md) | score against stated criteria with a quote per score |
| [improve-writing](./references/patterns/improve-writing.md) | same meaning, clearer, voice intact |
| [review-code](./references/patterns/review-code.md) | defects with location, mechanism, and fix |
| [explain-code](./references/patterns/explain-code.md) | purpose, mechanism, invariants, failure behavior |
| [explain-error](./references/patterns/explain-error.md) | message to cause to discriminating check to fix |
| [write-tests](./references/patterns/write-tests.md) | tests that fail when behavior regresses |
| [refactor-plan](./references/patterns/refactor-plan.md) | behavior-preserving restructuring, mergeable in pieces |
| [api-design-review](./references/patterns/api-design-review.md) | review an interface from the caller's position |
| [threat-model](./references/patterns/threat-model.md) | assets, boundaries, threats ranked by attacker cost |
| [data-quality-review](./references/patterns/data-quality-review.md) | the failures that produce confidently wrong numbers |
| [compare-options](./references/patterns/compare-options.md) | real alternatives on decision-relevant dimensions |
| [write-adr](./references/patterns/write-adr.md) | an architecture decision record that ages well |
| [draft-pr-description](./references/patterns/draft-pr-description.md) | what a reviewer needs, in the order they need it |
| [create-checklist](./references/patterns/create-checklist.md) | a list usable under time pressure |
| [create-mermaid](./references/patterns/create-mermaid.md) | a diagram that renders and shows the mechanism |
| [meeting-notes](./references/patterns/meeting-notes.md) | decisions and owned actions out of a transcript |

## Output contract

The output is the chosen pattern's own contract, unchanged, under a two-line header that names the pattern applied and the input it was applied to. Where a run adds a section the pattern does not define, the section is labelled as an addition. Where a pattern's section is empty because the input had nothing for it, say so rather than deleting the heading.

## Tool contract

<!-- keep: tool-contract -->
```
python .github/skills/Fabric/fabric_list.py                    # name and purpose per pattern
python .github/skills/Fabric/fabric_list.py --json             # machine index
python .github/skills/Fabric/fabric_list.py <pattern>          # print one pattern's full text
python .github/skills/Fabric/fabric_list.py <pattern> --json   # pattern metadata plus body
python .github/skills/Fabric/fabric_list.py --help             # usage, exit 0
```

`--dir` overrides the pattern directory. Exit codes are 0 for a run, 1 for an unknown pattern or empty directory, 2 for usage.

## Roles

Most patterns run at the **high** role. Route the judgment-heavy ones — threat-model, compare-options, write-adr, api-design-review, analyze-claims — to the **max** role, because their value is entirely in the quality of the ranking. Mechanical ones such as summarize and meeting-notes run fine at the **medium** role. Patterns applied to another model's output should run at the **cross** role from a different vendor family.

## Constraints and gotchas

- Two patterns on one input produce two reports, not one blended one. Run them separately and say which is which.
- A pattern is a floor, not a ceiling. If the input calls for something the pattern does not cover, add a section and label it as an addition.
- Patterns do not fetch. Retrieve the source first, by reading the file or fetching the page, then apply the pattern to what you actually have.
- Adding a pattern means adding a file to the pattern directory and a row to the table above. The tool picks it up automatically; the table does not.
