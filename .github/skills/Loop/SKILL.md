---
name: loop
description: "Runs the same prompt or skill repeatedly with a cadence and a stop rule, in an environment with no scheduler. Registers the loop, records each iteration's result and note so the next iteration starts from what the last one found, and finishes on a stated condition rather than running until someone notices. USE WHEN loop, run this repeatedly, every 30 minutes, on a cadence, keep checking, poll until, watch for, repeat until, run it again until it passes, periodic check, recurring task, background check, until there are no open PRs, keep going until green, iterate until, schedule this. NOT FOR improving one artifact toward a measurable target (use optimize), a one-off retry after a failure (just retry), or work that needs a real scheduler with guaranteed wall-clock timing."
argument-hint: "[cadence] <prompt or /skill>"
---

# Loop — repetition with a stop rule

## What this produces

A named loop with a recorded prompt, a cadence, a stop condition, and a history of what each iteration found. The state file is what makes iteration seven aware of what iteration six learned, since nothing else survives between sessions.

## Done looks like

- The loop is registered with a stop condition stated in words, not implied.
- Every iteration appended a result and a one-line note.
- The loop reached `finished` for a named reason, or `stopped` on request. A loop still `running` after the work is over is a defect.
- The stop condition was checked against evidence, not against a feeling that enough iterations had happened.

## USE WHEN

Something has to be checked until a condition holds: a queue draining, a build going green, PRs arriving, a migration finishing, a flaky test reproducing.

## NOT FOR

Hill-climbing one artifact toward a number (`optimize`). A single retry. Anything requiring guaranteed timing, because nothing here guarantees timing.

## There is no scheduler

Be honest about this up front, because the alternative is a loop that everyone believes is running and is not. This environment has no background timer and no cron. A loop runs when something triggers it, and there are three honest triggers:

| Trigger | How it works | Use when |
|---|---|---|
| The engineer re-invokes | `/loop` again, or just "next iteration" | iterations are minutes apart and someone is present |
| A task runner | a VS Code task or a terminal command bound to a key, running one iteration | the cadence is minutes and the work is mechanical |
| An external scheduler | the platform's own scheduler runs a command that records a tick | the cadence is hours or days and nobody will be watching |

The state file is what all three share. Whoever fires the iteration, the loop reads its own history first and writes its result last, so the record is continuous even when the trigger is not.

The cadence recorded in the loop is an *intent*, not a guarantee. Treat it as documentation of how often this should happen, and expect drift.

## The stop rule is the whole design

A loop without a stop rule is not a loop, it is a habit. Write the condition before the first iteration, in terms something can check:

- **Condition met** — "no open PRs against main", "the suite is green", "the backlog is under 100". This is the good case and it should be checkable with one command.
- **Iteration ceiling** — a hard maximum, always set. It is the backstop for a condition that turns out never to hold.
- **No-change ceiling** — stop after N iterations that changed nothing. Usually the real stop rule, because a loop that has stopped making progress is done whether or not its condition holds.
- **Failure** — stop on the first failure when iterations build on each other, keep going when they are independent. Decide which at registration, not during.

Record the result of each iteration as one of `ok`, `fail`, `nochange`, `blocked`. That vocabulary is small on purpose: it makes a run of `nochange` visible, which is the signal that matters most and the one a prose note hides.

## What each iteration does

An iteration is a full unit of work, not a fragment. It reads the loop's last note, does one pass, records what it found, and stops. It does not carry state in its head for the next one, because there may be no next one in this session.

Keep the per-iteration work small enough that an interrupted iteration loses nothing important. If one iteration takes an hour and cannot be resumed, the loop is the wrong shape and the work wants an ISA instead.

## Tool contracts

<!-- keep: tool-contract -->

| Command | Contract |
|---|---|
| `python .github/skills/Loop/loop_state.py start --name N --prompt P [--every 30m] [--max N] [--stop-when "…"]` | registers a loop. `--force` overwrites. Exit 1 if the name exists without `--force`. |
| `python .github/skills/Loop/loop_state.py tick --name N [--result ok\|fail\|nochange\|blocked] [--note "…"] [--done] [--stop-on-fail]` | records one iteration. Exit 0 while the loop continues, 1 when it finished, and the payload names the reason. |
| `python .github/skills/Loop/loop_state.py status [--name N]` | one loop or all of them, with iteration count and last result. |
| `python .github/skills/Loop/loop_state.py list` | the table of every loop. |
| `python .github/skills/Loop/loop_state.py stop --name N [--reason "…"]` | finishes a loop deliberately. |

Every subcommand takes `--state PATH` to override the state file and `--json` for machine output. State defaults to `$KAIOS_HOME/MEMORY/STATE/loops.json`.

The non-zero exit on the finishing tick is the useful part: a task runner that stops when the command returns non-zero needs no other logic.

## Constraints and gotchas

- Never register a loop without a maximum. The failure mode of an unbounded loop is not an infinite loop, it is a forgotten one that quietly stops being true.
- Record the tick even when the iteration did nothing. A gap in the history is indistinguishable from a gap in the loop.
- Do not put the loop's findings only in the note field. A note is one line; anything substantial belongs in a capture or the ISA, with the note pointing at it.
- Check the stop condition with a command, not by reading the last note. The note says what the previous iteration believed.
- A loop is not a way to make a hard problem easier by doing it repeatedly. If three iterations produce three different answers to the same question, stop and look at why.
- Clean up finished loops. A state file full of loops that ended months ago makes the running one hard to see.
