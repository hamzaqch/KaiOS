# Prompt templates

Starting points, not forms to fill blindly. Delete every section that would be empty.

## Skill

```markdown
---
name: <lowercase-hyphen, 64 chars or fewer>
description: <what it produces in one sentence>. USE WHEN <the words a person would actually type, comma separated>. NOT FOR <what it must not fire on, naming the neighbouring capability>.
argument-hint: "<what the user passes>"
---

# <Title>

<One or two sentences on why this exists. No marketing.>

## What this produces
<The artifact, then a bullet list of done-criteria a reader could check.>

## Output contract
<The headings, table columns, or schema the result must have.>

## Tool contract
<!-- keep: tool-contract -->
```
python .github/skills/<Name>/<tool>.py <args> [--json]
```
<Exit codes and output shape.>

## Roles
<Which role rung runs which part, and why a second look comes from another family.>

## Constraints and gotchas
<The things that go wrong, stated as rules with reasons.>
```

## Agent

```markdown
---
name: <role-name>
description: <when the orchestrator should hand work to this agent>
tools: [<tool names>]
model: <rendered from the registry — never hand-edited>
---

# kaios-role: <max | high | medium | cross | third | research>

<What this agent is responsible for, in outcome terms.>

## Done means
<Checkable criteria for this agent's output.>

## Boundaries
<What it must not do. Read-only agents say so here.>

## Handoff
<What it returns, and to whom.>
```

## Instruction file

```markdown
---
applyTo: "<glob>"
---

<Rules that apply only to files matching the glob. Each rule is one line,
checkable, and non-obvious. If a capable model would do it anyway, leave it out.>
```

## Review prompt

```
Review <artifact> for <the specific property>.

Done means every finding names the location, the mechanism by which it fails,
and a fix a builder could start today. Severity is one of critical, high,
medium, low. Findings you considered and rejected are listed with the reason.

Report as a table with columns: location | finding | severity | fix.
Do not edit the artifact.
```

## Judge prompt

```
Score <output> against these criteria, each independently.

| criterion | what full marks look like | what zero looks like |
|---|---|---|

Return JSON only, this shape:
{"scores": {"<criterion>": {"score": 0-5, "evidence": "<quote from the output>"}},
 "verdict": "pass|fail", "reason": "<one sentence>"}

Every score cites a quote from the output. A score with no quote is invalid.
Judge only what is present; do not reward intent.
```

## Extraction prompt

```
Extract <the target facts> from <the source>.

Done means every extracted item is traceable to a span in the source, items
absent from the source are omitted rather than inferred, and ambiguous cases
are listed separately under "uncertain" with the competing readings.

Return JSON only, this shape:
{"items": [{"value": "...", "source_span": "..."}], "uncertain": [...]}
```
