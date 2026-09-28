---
name: root-cause-analysis
description: Structured investigation of a failure that already happened, using Five Whys, a fishbone cause map, fault-tree decomposition, or FMEA depending on the failure shape, and ending in a blameless write-up with contributing causes, a timeline, and preventive actions with owners. Files the report to the incident log through the memory CLI so recurrences are visible. USE WHEN root cause, RCA, five whys, postmortem, incident, why did this break, why does this keep failing, it happened again, outage write-up, fishbone, fault tree, FMEA, recurring bug, regression that came back. NOT FOR modeling ongoing structural behavior with feedback loops (use systems-thinking), testing a hypothesis about a live mystery (use science), or attacking a plan that has not shipped (use red-team).
argument-hint: "<the incident or recurring failure> [--method five-whys|fishbone|fault-tree|fmea]"
---

# Root Cause Analysis

A failure is information about the system that produced it. This skill extracts that information without blaming a person.

## USE WHEN / NOT FOR

USE WHEN something broke and the cause is not yet systemic, or the same failure has now happened more than once.

NOT FOR modeling ongoing structural behavior, which is systems-thinking, or attacking a plan that has not shipped, which is red-team.

## What this produces

A write-up whose preventive actions would have stopped the failure, filed where the next person will find it.

## Done looks like

- A timeline exists with timestamps, from the first contributing change to detection to mitigation to resolution. Detection time is recorded separately from failure time, because the gap between them is usually the bigger problem.
- Causes are plural. Single-cause incidents are rare, and reporting one is usually where the investigation stopped early.
- Every cause is systemic rather than personal. "An engineer forgot the migration flag" is not a root cause; "the deploy path accepts a config with the flag absent and defaults it to on" is.
- Each causal step is supported by evidence, a log line, a diff, a metric, a config value, quoted in the report.
- Preventive actions are specific, owned, and verifiable, and each names the cause it removes. An action nobody owns does not exist.
- The report distinguishes what would have prevented the failure from what would have detected it faster. Both are needed; they are not the same work.

## Methods

| method | failure shape it fits | what it yields |
|---|---|---|
| five whys | a single clear failure chain | the chain from symptom down to a systemic cause |
| fishbone | many plausible contributors across categories | a cause map grouped by process, tooling, data, config, people-systems, environment |
| fault tree | a failure that required several conditions at once | the condition combinations that produce the top event |
| FMEA | prospective, before a launch or a migration | ranked failure modes by severity, likelihood, and detectability |

Five whys stops when the next "why" would name a person's mistake rather than a system that allowed it. If you land on a person, the previous answer was the real stopping point and the system question is what allowed that mistake to reach production.

## Output contract and where it is filed

The report is markdown with this shape, written to the incident log at `$KAIOS_HOME/MEMORY/LEARNING/INCIDENTS/INC-YYYYMMDD-<slug>.md`.

```
---
id: INC-YYYYMMDD-<slug>
severity: sev1|sev2|sev3
detected: <iso>
resolved: <iso>
method: five-whys|fishbone|fault-tree|fmea
---

# <one-line title, no names>

## Impact
<who or what was affected, for how long, how it was noticed>

## Timeline
| time | event | evidence |

## Causes
| # | cause | class | evidence | why it was possible |

## Why it was not caught sooner
<the missing test, alert, gate, or review>

## Preventive actions
| # | action | removes cause | owner | verified by |

## What went right
<the thing that limited the damage — keep it>
```

Register it through the memory CLI so recurrence shows up.

<!-- keep: tool-contract -->
```
python -m kaios memory capture --kind incident --text "<the report body or a path to it>"
```

The capture is what makes the third occurrence of a failure visible as a pattern rather than as a surprise.

## Roles

Run the causal reasoning at the **max** role. Evidence gathering, log reading, and diff archaeology run at the **high** role. When the incident involved a system the investigator also built, get the cause chain reviewed at the **cross** role from a different vendor family, for the same reason a builder does not audit their own work.

## Constraints and gotchas

- Blameless is a method, not a manner. It means the causes you write down must be things the system does, because those are the only ones you can fix.
- Reproduce before concluding where reproduction is possible. A plausible chain that cannot be demonstrated is a hypothesis; mark it as one.
- Do not let mitigation hide the cause. Restarting the service resolved the incident and explained nothing.
- Check whether this is a recurrence before writing. Search the incident log first; a second report on the same cause means the first set of actions was not done or not sufficient, and that is the finding.
- Keep the write-up short enough to be read. A report nobody finishes prevents nothing.
