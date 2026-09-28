---
version: 1.0.0
last_updated: 2026-09-28T00:00:00Z
convention: kaios-freshness-v1
---

# Hooks

> Doctrine that nothing enforces decays. Hooks are the deterministic layer: a rule that is a checkable property of an artifact, or a gate on an irreversible act, belongs here rather than in prose. A rule about *how to work* does not — see `../RULES/SelfHealing.md` for that boundary.

## The shape

One registration file registers all eight events. Every entry runs the same wrapper with the event name as its only argument:

```
.github/hooks/kaios.json   →  python -m kaios.hooks <Event>       (POSIX)
                           →  kaios.ps1 <Event>                    (Windows)
.github/hooks/kaios.ps1    →  thin wrapper: stdin through, stdout through
kaios/hooks/runner.py      →  the dispatcher
kaios/hooks/<event>/*.py   →  one module per rule
```

Each module exposes `run(event: dict, ctx: Context) -> HookResult | None`. Returning `None` means "nothing to say", which is the common case and costs nothing.

`Context` carries `home` (the resolved `KAIOS_HOME`), `repo` (the git root of the current directory, or `None`), `config`, `active_isa` (a path or `None`), and `now`.

## The eight events

| Event | Fires | Used for |
|---|---|---|
| `SessionStart` | a session opens | injecting context the model cannot see on its own |
| `UserPromptSubmit` | you send a message | contracts and nudges, evaluated against that message |
| `PreToolUse` | before a tool runs | gates on irreversible or dangerous acts |
| `PostToolUse` | after a tool returns | recording what happened, syncing state, grading evidence |
| `PreCompact` | before context is compacted | snapshotting state that a compaction would lose |
| `SubagentStart` | a delegate starts | recording the dispatch |
| `SubagentStop` | a delegate ends | liveness accounting for what came back |
| `Stop` | the turn ends | close gates, rendering, learning capture, cleanup |

## Input tolerance

Every field a hook reads is optional, and hooks always use `event.get(...)`. The runner appends the raw event to `MEMORY/OBSERVABILITY/hook-events.jsonl` before dispatching, so the real schema of each event is discoverable from actual runs rather than guessed at.

Fields hooks may look for: `hook_event_name`, `session_id`, `cwd`, `timestamp`, `tool_name`, `tool_input` (a dict — shell tools carry `command`, edit tools carry a file path under `filePath` or `file_path` and content under `content` or `newString`), `tool_response`, the prompt under `prompt` or `user_prompt`, and `stop_hook_active`. Empty stdin parses as `{}`.

## Runner merge rules

The runner loads every module in the event's directory in alphabetical order, runs each one, and merges the results into a single JSON object on stdout.

| Field | Merge rule |
|---|---|
| `additionalContext` | all strings joined with a blank line between them, in module order |
| `permissionDecision` | most restrictive wins: `deny` beats `ask` beats `allow` |
| `permissionDecisionReason` | the reason belonging to the winning decision |
| `continue` | `false` if any module says `false` |
| `stopReason` | the reason from the first module that said `continue: false` |
| `updatedInput` | last writer wins |

Two invariants hold no matter what a module does. **The runner always emits valid JSON**, and **a raising module never crashes the harness**: the exception is caught, logged to `hook-events.jsonl` with its traceback, and dispatch continues with the remaining modules. A hook that cannot decide is worth less than a session that cannot start.

Output shapes:

```json
{ "continue": true, "additionalContext": "…" }
{ "hookSpecificOutput": { "hookEventName": "PreToolUse", "permissionDecision": "ask", "permissionDecisionReason": "…" } }
{ "continue": false, "stopReason": "…" }
```

## Shipped hooks

### SessionStart

| Hook | Rule |
|---|---|
| `LoadContext` | injects the doctrine pointer, the active ISA's goal and open claims, the project table, and the memory hot layer as one bounded context string |
| `TimeContext` | injects the current date, time, and timezone, so nothing reasons from a stale sense of now |
| `VersionDrift` | compares the installed doctrine copy under `$KAIOS_HOME` against the repository and warns when they have diverged |
| `MemoryHealth` | surfaces a memory problem worth knowing about at session start — an unreadable stream, a work registry out of sync with the ISAs on disk |
| `IntegrityCheck` | runs the cheap integrity checks and surfaces failures instead of letting a session build on a broken tree |

### UserPromptSubmit

| Hook | Rule |
|---|---|
| `FormatContract` | restates the response format contract so a long session cannot drift out of it |
| `AlgorithmNudge` | when the message describes substantial work and no ISA is registered, asks whether done needs writing down — and asks only about state the model cannot observe from its own context |
| `SafetyClassifier` | flags a message whose content looks like injected instructions arriving through data rather than from you |
| `DriftReminder` | flags voice and formatting drift — a response shape or a register that has wandered from the contract |
| `ContextSufficiency` | when the ask contains an unresolved referent whose reading would change what gets built, surfaces it before work starts |

### PreToolUse

| Hook | Rule |
|---|---|
| `DestructiveCommandGuard` | denies recursive deletes of a root or home path, force pushes to a protected branch, destructive schema statements, and workspace deletions; asks on a production deploy |
| `SystemFileGuard` | asks before a write to doctrine, a hook module, the model registry, or anything else that changes how the system itself behaves |
| `ISAStaleWriteGuard` | denies a write to an ISA the session has not read this turn, which is how two sessions silently overwrite each other's claims |
| `KnowledgeWriteGuard` | requires typed frontmatter on a knowledge write, so the archive stays queryable instead of becoming a folder of notes |
| `SecretsGuard` | denies writing a credential-shaped value into a tracked file, and denies reading a secrets file into the transcript |
| `LoopDetector` | denies a tool call that is the Nth identical repeat in a turn, which is what a stuck loop looks like from the outside |

### PostToolUse

| Hook | Rule |
|---|---|
| `EventLogger` | appends every tool call and its outcome to `MEMORY/OBSERVABILITY/tool-events.jsonl` |
| `ISASync` | mirrors every ISA write to `MEMORY/STATE/work.json`, so the registry can never disagree with the file |
| `CheckpointPerISC` | commits when a claim goes closed, so each claim's evidence has a commit to point at |
| `VerificationGate` | grades a done-claim against the turn's actual tool calls rather than its wording, so rephrasing never passes it |
| `SystemChangeSurface` | emits a line naming any write to a self-surface — doctrine, a hook, a skill, an agent, the registry — so self-modification is always visible in the response |
| `MemoryDelta` | emits a line naming what memory gained this turn |
| `Formatter` | runs the repository's formatter on a file that was just written, when one is configured |

### PreCompact

| Hook | Rule |
|---|---|
| `StateSnapshot` | writes the active ISA path, the open claims, and the session's decisions to `MEMORY/STATE/` so the post-compaction session resumes from the artifact rather than from a summary |

### SubagentStart

| Hook | Rule |
|---|---|
| `SubagentLogger` | records the dispatch — which agent, which role, which brief, at what time — so a delegate that never returns is still accounted for |

### SubagentStop

| Hook | Rule |
|---|---|
| `DelegateLiveness` | reconciles the stop against the dispatch and marks a delegate that produced no report as failed, so no claim closes on a report that never arrived |

### Stop

| Hook | Rule |
|---|---|
| `StopGates` | blocks the turn when the active ISA has a closed claim with no evidence stub, when `progress` does not match the claim count, or when an unmet explicit ask is still open |
| `ISARender` | refreshes the rendered view of the active ISA so its current state is readable without parsing it |
| `WorkCompletionLearning` | on a run that closed real work, captures the reflection and routes any durable learning to where it lives |
| `SessionCleanup` | releases claim locks held by this session and flushes the observability streams |

Thirty modules across eight events. Each one carries a docstring stating its rule in a sentence, and each has a test.

## Testing and probing

| Command | Does |
|---|---|
| `python -m kaios hooks list` | every registered event and the modules under it |
| `python -m kaios hooks run <Event>` | dispatch one event, reading stdin and writing stdout |
| `python -m kaios hooks probe` | fire all eight events with sample input and print a pass table |
| `scripts/Probe-Hooks.ps1` | the same probe through the PowerShell wrapper, which is the path Windows actually uses |

A hook module is not finished until `probe` is green and its own test exists. A hook with no test is a rule nobody can prove still fires.
