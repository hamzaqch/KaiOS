---
name: suggest-skills
description: Decide which skills are worth building next by reading your own work history instead of guessing. Tallies recurring themes and friction markers across memory captures and the work registry, checks each theme against the skills that already exist, and hands back a ranked shortlist with the evidence behind each candidate. Proposal only — it never creates or edits a skill. USE WHEN what skills should I build, suggest skills, skill gaps, am I missing a skill, based on my recent work, what keeps costing me time, what should I automate next, review my captures for patterns, do I need a skill for this. NOT FOR creating, editing, validating, or testing an individual skill (use create-skill), or proposing a skill from a single frustrating afternoon rather than from recorded history.
argument-hint: "[--top N] [--min-count N]"
---

# Suggest Skills

The best evidence for what to build is what already keeps happening. This reads the record rather than the mood.

## USE WHEN / NOT FOR

USE WHEN you want the next skill chosen by recorded history rather than by the most recent annoyance.

NOT FOR creating, validating, or testing a skill, which is create-skill. This one proposes and never writes.

## What this produces

A ranked shortlist a person can act on, and nothing else.

## Done looks like

- Every candidate is backed by counted occurrences across captures or work items, with a sample quoted. A candidate with no evidence is an opinion and does not belong on the list.
- Recurrence and friction are reported separately. A topic appearing often because the work is routine is not the same as a topic appearing often because it keeps going wrong, and only the second one justifies building something.
- Each candidate says whether an existing skill already covers the theme. A theme can be nominally covered and still painful, and that case is reported as sharpen the existing skill rather than build a new one.
- Each proposal states what the skill would produce and what its done-criteria would be, because a proposal nobody can evaluate is a wish.
- Candidates that were considered and rejected are listed with the reason, so the same theme is not re-proposed next month.
- Nothing is created. The output ends with a handoff, not a file.

## Signals worth weighting

| signal | why it matters |
|---|---|
| repeated theme across separate captures | the work recurs, so tooling amortizes |
| friction markers such as again, still, by hand, every time | the recurrence costs something |
| incidents on the same subject | the failure mode is systemic, not bad luck |
| a low-rated session on a topic that also recurs | covered on paper, failing in practice |
| work items whose goals restate each other | the same problem being re-solved |

A theme needs both recurrence and cost. Frequent and painless is a habit, not a gap. Rare and painful is an incident, and root-cause-analysis is the right response.

## Output contract

```
## Evidence base
<captures read, work items read, date range, existing skills counted>

## Candidates
| # | proposed skill | theme | occurrences | friction | covered by | verdict |

## Top proposals
### <proposed-name>
what it would produce:
done would mean:
why now:
evidence:
build | sharpen existing | not yet — <reason>

## Rejected
<theme — why it does not justify a skill>

## Handoff
<which proposals to take to create-skill, in order>
```

## Tool contract

<!-- keep: tool-contract -->
```
python .github/skills/SuggestSkills/suggest_skills.py
python .github/skills/SuggestSkills/suggest_skills.py --top 15 --min-count 2 --json
python .github/skills/SuggestSkills/suggest_skills.py --home <memory root> --skills-dir <dir>
python .github/skills/SuggestSkills/suggest_skills.py --help
```

It reads capture JSONL files anywhere under the memory tree (skipping the observability logs) plus `MEMORY/STATE/work.json`, and resolves the memory root from `--home`, then `KAIOS_HOME`, then the default home. Output is a table by default and `{"memory", "sources", "captures", "work_items", "existing_skills", "candidates", "note"}` with `--json`. Each candidate carries term, occurrences, friction, score, covered_by, and a sample. Missing memory is not an error; it exits 0 with a note. The tool writes nothing.

## Roles

Run the tool at the **medium** role, since it is counting. Turn counts into proposals at the **max** role, because deciding that a recurring theme deserves a skill rather than a one-line instruction or a fix to an existing skill is exactly the judgment that keeps a skill library small.

## Constraints and gotchas

- Word counts are a pointer, not a conclusion. The tool finds that a term recurs; only a person can say whether a skill is the right response.
- Prefer sharpening an existing skill to adding a new one. Two overlapping skills both trigger and each does the job worse.
- A theme that recurs because of a missing tool wants a tool, and a theme that recurs because of a missing instruction wants one line in an instruction file. Neither needs a skill.
- Do not propose more than three skills at once. A shortlist nobody builds is the same as no shortlist.
- Never create files here. Proposal only, every run.
