"""The eight harness events KaiOS hooks into, and their directory names.

This module is the one place the event list is written in Python. It imports
nothing from the rest of the package on purpose, so any layer — the hook runner,
setup, the probe — can depend on it without a cycle.

The checked-in registry ``.github/hooks/kaios.json`` is the authority when a
checkout is present; :func:`registry_events` reads it, and ``EVENTS`` is the
default for an install with no checkout beside it. ``tests/test_events.py``
fails if the two ever disagree.
"""

from __future__ import annotations

import json
from pathlib import Path

#: Ordered by when the event fires in a session. Must match the event keys in
#: ``.github/hooks/kaios.json`` and the hook module directories under
#: ``kaios/hooks/``.
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

#: Where the authoritative registry lives inside a checkout.
REGISTRY_RELATIVE = ".github/hooks/kaios.json"


def registry_events(root: Path | str, strict: bool = False) -> tuple[str, ...]:
    """The event keys in a checkout's hook registry, or ``EVENTS`` if unreadable.

    Pass ``strict=True`` to raise instead of falling back, which is what a test
    wants: a silent fallback would hide exactly the drift this guards against.
    """
    path = Path(root) / REGISTRY_RELATIVE
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        hooks = data["hooks"]
        if not isinstance(hooks, dict) or not hooks:
            raise ValueError("%s has no hooks object" % path)
        return tuple(hooks.keys())
    except (OSError, ValueError, KeyError, TypeError):
        if strict:
            raise
        return EVENTS


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
