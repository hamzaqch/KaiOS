---
version: 1.1.0
last_updated: 2026-09-28T00:00:00Z
convention: kaios-freshness-v1
---

# Hooks

> Doctrine that nothing enforces decays. Hooks are the deterministic layer: a rule that is a checkable property of an artifact, or a gate on an irreversible act, belongs here rather than in prose. A rule about *how to work* does not — see `../RULES/SelfHealing.md` for that boundary.

## The shape

One registration file registers all eight events. Every entry runs the same wrapper with the event name as its only argument:

```
.github/hooks/kaios.json   →  kaios.ps1 <event>                    (Windows)
                           →  kaios.sh  <event>                    (POSIX)
.github/hooks/kaios.ps1    →  thin wrapper: stdin through, stdout through
.github/hooks/kaios.sh     →  the same wrapper for a POSIX host
kaios/hooks/runner.py      →  the dispatcher
kaios/hooks/<event>/*.py   →  one module per rule
```

Why one file has two entry shapes in it, and why six of its keys are camelCase: § Two Copilot engines, one registry, below.

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

The Copilot CLI engine sends the same fields in camelCase, so every reader in `kaios/hooks/util.py` accepts both spellings: `sessionId` for the session, `toolName` for the tool, `toolArgs` for its arguments, `toolResult` for what came back. Reading only the snake_case name is a silent failure rather than a loud one — a guard handed `toolArgs` it does not know about sees an argument-less tool call and waves it through.

## Runner merge rules

The runner loads every module in the event's directory in alphabetical order, runs each one, and merges the results into a single JSON object on stdout.

| Field | Merge rule |
|---|---|
| `additionalContext` | all strings joined with a blank line between them, in module order |
| `permissionDecision` | most restrictive wins: `deny` beats `ask` beats `allow` |
| `permissionDecisionReason` | the reason belonging to the winning decision |
| `continue` | `false` if any module says `false` |
| `stopReason` | the reasons from every module that said `continue: false`, joined |
| `updatedInput` | last writer wins |

Two invariants hold no matter what a module does. **The runner always emits valid JSON**, and **a raising module never crashes the harness**: the exception is caught, logged to `hook-events.jsonl` with its traceback, and dispatch continues with the remaining modules. A hook that cannot decide is worth less than a session that cannot start.

Every decision is then written twice, once in each dialect (§ Two Copilot engines, one registry). Both halves say the same thing, and the half an engine does not read is inert to it:

```json
{ "continue": true, "additionalContext": "…" }

{ "permissionDecision": "deny", "permissionDecisionReason": "…",
  "hookSpecificOutput": { "hookEventName": "PreToolUse",
                          "permissionDecision": "deny", "permissionDecisionReason": "…" } }

{ "continue": false, "stopReason": "…", "decision": "block", "reason": "…" }
```

`additionalContext` is the one field both dialects spell the same way. `decision` is emitted only on a block, because the CLI engine reads the bare presence of that key as the verdict.

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
| `python -m kaios hooks probe` | fire all eight events in both dialects with sample input and print a pass table |
| `scripts/Probe-Hooks.ps1` | the same probe through the PowerShell wrapper, which is the path Windows actually uses |

The probe fires sixteen rows, not eight: one per event per dialect, from `kaios/hooks/samples.py`. A guard that reads `tool_input` and not `toolArgs` passes an eight-row probe and then waves through every tool call the CLI engine sends, so the doubling is the point.

A hook module is not finished until `probe` is green and its own test exists. A hook with no test is a rule nobody can prove still fires.

## Where the wrapper finds the package

Both wrappers resolve `import kaios` from, in order: `KAIOS_REPO` (set by `Install.ps1`), `%KAIOS_HOME%\lib` (a package copy `Install.ps1` refreshes on every run), then the repo the wrapper lives in. Each sets `PYTHONPATH` for the child process, runs it with that directory as the working directory, and logs any child stderr to `MEMORY/OBSERVABILITY/hook-errors.log` instead of the console, because a harness that sees stderr may fail closed and deny the tool call. `KAIOS_HOOKS_DISABLED=1` is the kill switch for both.

`Install.ps1` copies both wrappers to `%USERPROFILE%\.copilot\hooks\` and points the user-level registry at those copies, so hooks keep working when the checkout moves.

## Two Copilot engines, one registry

Copilot in VS Code ships **two** hook engines, and they do not read the same dialect. Keep-class: this cost a field outage — every tool call denied, the registry reported as needing repair — and nothing about either file looks wrong until you know this.

| | VS Code "Local" engine | Copilot CLI engine (Agent Host, `copilot`) |
|---|---|---|
| Event keys | PascalCase: `SessionStart`, `PreToolUse`, `PreCompact`, `SubagentStart`, … | camelCase: `sessionStart`, `preToolUse`, `userPromptSubmitted`, `agentStop`, … |
| Also accepts | the camelCase names below, and `bash` / `powershell` / `timeoutSec` entry keys | PascalCase keys, parsed with Claude semantics: `{ "hooks": [ { "type": "command", "command": "…" } ] }` |
| Entry keys | `command`, `windows`, `timeout` | `bash`, `powershell`, `cwd`, `env`, `timeoutSec` |
| Unparseable item | tolerated | **dropped and logged**, and the file is reported as needing repair |
| A failing `preToolUse` hook | tool proceeds | **fails closed — the tool call is denied** |
| Reads a tool decision from | `hookSpecificOutput.permissionDecision` | top-level `permissionDecision` |

The two vocabularies overlap but do not match. Six events exist in both: `sessionStart`, `userPromptSubmitted`, `preToolUse`, `postToolUse`, `subagentStop`, `agentStop`. Two do not — the CLI engine's camelCase table has no `preCompact` or `subagentStart` that the Local engine also maps.

So the registry is written in whichever dialect each event is understood in, and the spelling decides the entry shape:

| Event | Registry key | Entry shape | Read by |
|---|---|---|---|
| `SessionStart` | `sessionStart` | flat `bash` + `powershell` + `timeoutSec` | both engines |
| `UserPromptSubmit` | `userPromptSubmitted` | flat | both |
| `PreToolUse` | `preToolUse` | flat | both |
| `PostToolUse` | `postToolUse` | flat | both |
| `PreCompact` | `PreCompact` | Claude nested `{ "hooks": [ … ] }` | Local natively, CLI under Claude semantics |
| `SubagentStart` | `SubagentStart` | Claude nested | Local natively, CLI under Claude semantics |
| `SubagentStop` | `subagentStop` | flat | both |
| `Stop` | `agentStop` | flat | both |

Nothing fires twice, because each name exists in only one of the two parsers' tables: a camelCase key is one entry in each engine's map, and a PascalCase key is likewise one. That is also why the two PascalCase events must not be *also* listed in camelCase as a belt-and-braces measure — that is precisely what would double-fire them in the Local engine.

Three consequences worth stating plainly:

- **JSON has no comments**, so none of this is written in the file. This section is the explanation; `tests/test_registry_dialects.py` is the enforcement, and it fails if a shared event goes PascalCase, if a flat entry picks up `command`/`windows`/`timeout`, or if either nested event loses its shape.
- **Rendering must not normalise the file.** `kaios setup render` and `Install.ps1` rewrite wrapper paths to absolute ones and change nothing else — not the key spelling, not the entry shape.
- **`kaios.events.canonical` is the translator.** Everything that reads a registry or an event name goes through it, so the rest of the package only ever sees the eight names in `EVENTS`. `userPromptSubmitted` → `UserPromptSubmit`, `agentStop` → `Stop`, `sessionEnd` → nothing, because that is an event the CLI engine has and KaiOS does not.
