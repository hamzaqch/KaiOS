"""The eight harness events KaiOS hooks into, and their directory names.

One place so the hook runner, the hook registry template, and the probe all
agree. ``EVENTS`` is ordered by when the event fires in a session.
"""

from __future__ import annotations

#: Must match the event keys in ``.github/hooks/kaios.json`` and the hook module
#: directories under ``kaios/hooks/``. That registry is the source of truth at
#: render time; this tuple is the default for an install with no checkout beside
#: it, and what ``canonical`` validates against.
EVENTS: tuple[str, ...] = (
    "SessionStart",
    "UserPromptSubmit",
    "PreToolUse",
    "PostToolUse",
    "PreCompact",
    "SubagentStart",
    "SubagentStop",
    "Stop",
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
