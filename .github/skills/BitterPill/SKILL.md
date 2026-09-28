---
name: bitter-pill
description: Audit an instruction set for over-prompting. Runs five questions against every rule, classifies each as CUT, RESOLVE, MERGE, EVALUATE, SHARPEN, MOVE, or KEEP, and reports an estimated token saving with the risk of each cut. The governing test is whether a more capable model makes the rule unnecessary, because scaffolding written for a weaker model becomes noise that crowds out the rules that matter. USE WHEN bitter pill, audit my instructions, too many rules, over-prompting, trim the prompt, is this rule needed, the instructions are bloated, clean up the constitution, my agent ignores its rules, prompt is too long, why is context so full. NOT FOR writing new instructions from scratch (use prompting), removing stale entries from a file mechanically, or reviewing application code.
argument-hint: "<instruction file or directory> [--quick]"
---

# Bitter Pill

Every rule in an instruction set competes for attention with every other rule. A file of two hundred rules enforces none of them.

## USE WHEN / NOT FOR

USE WHEN an instruction set has grown faster than it has been pruned, or an agent ignores rules that are present and correctly worded.

NOT FOR writing new instructions, which is prompting, or reviewing application code.

## What this produces

A per-rule verdict with an estimated saving and an honest risk note.

## Done looks like

- Every rule in the target is classified. A rule skipped because it looked fine is the rule that survives every audit and helps nothing.
- Each classification carries a one-line reason tied to one of the five questions.
- The token saving is estimated from measurement, not guessed. Run the bundled tool and quote its numbers.
- Each CUT names what breaks if the rule is gone, and says whether that risk is acceptable. A cut with no stated risk has not been thought about.
- Contradictions are reported as their own finding, because two rules that disagree are worse than either rule alone, and the audit must say which one wins.
- The output is a proposal. This skill never edits the target file; the owner decides.

## The five questions

Ask all five of every rule. Most rules fail at least one.

| question | what a failure means |
|---|---|
| Would a capable model do this anyway? | the rule is teaching table stakes — CUT |
| Does it contradict another rule? | pick a winner — RESOLVE |
| Does another rule already say this? | one of them goes — MERGE |
| Was it written to patch one bad output? | a one-off fix frozen into doctrine — EVALUATE |
| Is it too vague to check? | nobody can tell whether it was followed — SHARPEN |

Then one more, about placement rather than content: is this rule always relevant, or only in one context? Always-loaded files should hold only always-relevant rules. Everything else MOVEs to a path-scoped instruction file, a skill, or an agent.

## Classes

| class | meaning | action |
|---|---|---|
| CUT | a capable model does this without being told | delete |
| RESOLVE | conflicts with another rule | decide which governs, delete the loser |
| MERGE | duplicates another rule | fold into one sharper rule |
| EVALUATE | written to patch one incident | keep only if the incident would recur |
| SHARPEN | right idea, uncheckable wording | rewrite with an observable test |
| MOVE | correct but not always relevant | relocate to the scoped surface that needs it |
| KEEP | load-bearing, specific, non-obvious | leave untouched, and say why |

KEEP is the interesting class. A rule earns it by encoding something the model cannot infer: a local convention, a workplace constraint, a mistake with a cost, an interface only this team has.

## Output contract

```
## Measurement
<tool output — total tokens, the heaviest sections, flagged step blocks>

## Verdicts
| # | rule (quoted or located) | class | question it failed | reason | est. tokens |

## Contradictions
| rules | conflict | which should govern |

## Proposed saving
before ~<N> tokens → after ~<M> tokens (<P>% lighter)

## Risk register
| cut | what could regress | acceptable? |

## Keep list
<the rules that earn their place, with the reason each is non-obvious>
```

## Tool contract

<!-- keep: tool-contract -->
```
python .github/skills/BitterPill/bitter_pill.py <file.md>          # human table
python .github/skills/BitterPill/bitter_pill.py <file.md> --json   # machine report
python .github/skills/BitterPill/bitter_pill.py --help             # usage, exit 0
```

It reports per-section line, character, and approximate token counts (characters divided by four), and flags numbered-step blocks longer than eight items unless a `<!-- keep:` comment appears within the ten lines above the block. Exit codes are 0 for a run, 1 for a missing file, 2 for usage. The token figures are estimates for ranking sections against each other, not exact accounting.

## Roles

Run at the **max** role. Deciding that a rule is unnecessary requires knowing what a capable model does unprompted, which is exactly the judgment a weaker model lacks. A **cross** role second pass from a different vendor family is valuable on the CUT list, since every family has rules it needs that another does not.

## Constraints and gotchas

- Propose, never apply. The owner of an instruction set has context the audit does not, especially about incidents that produced a rule.
- Quote the rule you are cutting. An audit that refers to rules by paraphrase cannot be checked.
- Never cut a safety gate, a destructive-command guard, or a legal or compliance requirement on the grounds that a good model would behave well anyway. Those exist for the case where it does not.
- Step choreography is the densest form of over-prompting. Long numbered procedures in a prompt describe how, when the prompt should state what done looks like, so flag them even when each individual step looks reasonable.
- Length is a symptom, not the disease. Measure, but classify on content.
