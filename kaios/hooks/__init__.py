"""The hook layer: eight harness events, one runner, one module per rule.

Rule: doctrine that nothing enforces decays, so every rule that is a checkable
property of an artifact or a gate on an irreversible act lives here as a module
under ``kaios/hooks/<event_snake>/``.
Falsifier: ``python -m kaios hooks list`` shows fewer than eight events or
fewer than 25 modules, or ``python -m kaios hooks probe`` reports a failing row.

This module holds only the event vocabulary so that importing it is cheap and
cannot cycle: the dispatcher lives in :mod:`kaios.hooks.runner`.
"""

from __future__ import annotations

#: Every event KaiOS registers, in the order it fires during a session.
EVENTS: tuple = (
    "SessionStart",
    "UserPromptSubmit",
    "PreToolUse",
    "PostToolUse",
    "PreCompact",
    "SubagentStart",
    "SubagentStop",
    "Stop",
)

__all__ = ["EVENTS", "event_dir", "canonical"]


def event_dir(event: str) -> str:
    """``SessionStart`` -> ``session_start``: the hook package directory name."""
    out: list = []
    for index, char in enumerate(str(event)):
        if char.isupper() and index > 0:
            out.append("_")
        out.append(char.lower())
    return "".join(out)


def canonical(event: str) -> str | None:
    """Match an event name case-insensitively, tolerating snake_case input."""
    wanted = str(event).replace("_", "").replace("-", "").lower()
    for known in EVENTS:
        if known.lower() == wanted:
            return known
    return None
