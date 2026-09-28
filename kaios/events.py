"""The eight harness events KaiOS hooks into, and their directory names.

One place so the hook runner, the hook registry template, and the probe all
agree. ``EVENTS`` is ordered by when the event fires in a session.
"""

from __future__ import annotations

EVENTS: tuple[str, ...] = (
    "SessionStart",
    "UserPromptSubmit",
    "PreToolUse",
    "PostToolUse",
    "Stop",
    "SubagentStop",
    "PreCompact",
    "SessionEnd",
)


def event_dir(event: str) -> str:
    """``SessionStart`` -> ``session_start``; the hook package directory name."""
    out: list[str] = []
    for index, char in enumerate(event):
        if char.isupper() and index > 0:
            out.append("_")
        out.append(char.lower())
    return "".join(out)


def canonical(event: str) -> str | None:
    """Match an event name case-insensitively, tolerating snake_case input."""
    wanted = event.replace("_", "").replace("-", "").lower()
    for known in EVENTS:
        if known.lower() == wanted:
            return known
    return None
