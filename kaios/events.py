"""The eight harness events KaiOS hooks into, and their directory names.

This module is the one place the event list is written in Python. It imports
nothing from the rest of the package on purpose, so any layer — the hook runner,
setup, the probe — can depend on it without a cycle.

A hook registry is the authority wherever one exists — the checked-in
``.github/hooks/kaios.json`` in a checkout, or the rendered copy at
``$KAIOS_HOME/hooks/kaios.json`` on an installed machine. ``EVENTS`` is the
default for neither being reachable. ``tests/test_events.py`` fails if the tuple
and the checked-in registry ever disagree.

Two readers, because callers need different failure behaviour.
:func:`read_registry` takes a path and raises, for a caller that must report a
missing or malformed registry rather than paper over it — a count that silently
falls back to ``EVENTS`` would claim eight events for a registry that has none.
:func:`registry_events` takes a repository root and falls back, for a caller that
just needs a usable list.
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

#: Where ``setup render`` writes the installed copy, relative to KAIOS_HOME.
INSTALLED_REGISTRY_RELATIVE = "hooks/kaios.json"


def read_registry(path: Path | str) -> tuple[str, ...]:
    """The event keys in the registry at ``path``, in file order.

    Path-addressed and strict: raises ``OSError`` if the file is unreachable and
    ``ValueError`` if it is not a registry. Never substitutes ``EVENTS``, so a
    caller reporting how many events are registered cannot accidentally report
    the default for a registry that is missing or malformed.
    """
    target = Path(path)
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise ValueError("%s is not valid JSON: %s" % (target, exc)) from exc
    if not isinstance(data, dict):
        raise ValueError("%s is not a JSON object" % target)
    hooks = data.get("hooks")
    if not isinstance(hooks, dict) or not hooks:
        raise ValueError("%s has no hooks object" % target)
    return tuple(hooks.keys())


def registry_events(root: Path | str, strict: bool = False) -> tuple[str, ...]:
    """The event keys in a checkout's hook registry, or ``EVENTS`` if unreadable.

    Repository-root addressed, for a caller that just needs a usable list. Pass
    ``strict=True`` to raise instead of falling back, which is what a drift test
    wants: a silent fallback would hide exactly the disagreement it guards.
    """
    try:
        return read_registry(Path(root) / REGISTRY_RELATIVE)
    except (OSError, ValueError):
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
