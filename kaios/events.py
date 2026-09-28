"""The eight harness events KaiOS hooks into, and their directory names.

This module is the one place the event list is written in Python. It imports
nothing from the rest of the package on purpose, so any layer — the hook runner,
setup, the probe — can depend on it without a cycle.

``EVENTS`` holds KaiOS's own spelling of each event. A registry file spells them
differently, because the two hook engines Copilot ships do not share one
vocabulary: see ``REGISTRY_EVENT_NAMES`` below and the "Two Copilot engines, one
registry" section of ``SYSTEM/DOCUMENTATION/Hooks.md``. Everything that reads a
registry canonicalizes through :func:`canonical`, so the rest of the package
only ever sees the names in ``EVENTS``.

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

#: Where the authoritative registry lives inside a checkout. This is the one
#: definition of that path; ``setup`` and ``doctor`` import it rather than
#: spelling it again. The installed copy's location is deliberately NOT here:
#: ``Paths.hooks_json`` owns it, because resolving locations under KAIOS_HOME is
#: what ``paths`` is for, and a second definition is the problem we removed.
REGISTRY_RELATIVE = ".github/hooks/kaios.json"

#: The key spelling KaiOS ships for each event, so a rendered registry and a
#: checked-in one cannot drift apart. Six events are written in the Copilot CLI
#: engine's camelCase, which the VS Code engine also accepts. ``PreCompact`` and
#: ``SubagentStart`` are not in that engine's camelCase vocabulary at all, so
#: they ship PascalCase, which the VS Code engine reads natively and the CLI
#: engine reads under Claude semantics. Neither event fires twice in either
#: engine, because each name exists in only one of the two parsers' tables.
REGISTRY_EVENT_NAMES: dict = {
    "SessionStart": "sessionStart",
    "UserPromptSubmit": "userPromptSubmitted",
    "PreToolUse": "preToolUse",
    "PostToolUse": "postToolUse",
    "PreCompact": "PreCompact",
    "SubagentStart": "SubagentStart",
    "SubagentStop": "subagentStop",
    "Stop": "agentStop",
}

#: The events whose registry entry is the Claude-nested ``{"hooks": [...]}``
#: shape rather than a flat ``bash``/``powershell`` entry. Derived rather than
#: declared twice: an event shipped under its PascalCase name is the one the CLI
#: engine has to read with Claude semantics, and that shape is what it expects.
NESTED_REGISTRY_EVENTS: tuple = tuple(
    event for event in EVENTS if REGISTRY_EVENT_NAMES[event] == event
)

#: Event names the Copilot CLI engine uses that are not a case variant of ours.
#: ``None`` means the engine has the event and KaiOS does not, so a registry
#: naming it is read as registering nothing rather than as malformed.
_ALIASES: dict = {
    "userpromptsubmitted": "UserPromptSubmit",
    "agentstop": "Stop",
    "sessionend": None,
}


def registry_key(event: str) -> str:
    """The key spelling to write into a registry for one event."""
    name = canonical(event) or str(event)
    return REGISTRY_EVENT_NAMES.get(name, name)


def registered_events(hooks: dict) -> list:
    """The canonical events a registry's ``hooks`` object registers, in order.

    One definition, because two readers need it: :func:`read_registry` for a file
    on disk and ``kaios.setup`` for the object it is about to render. Both have to
    agree on what counts — a key canonicalizes, and it has at least one entry.
    """
    found: list = []
    for key, entries in (hooks or {}).items():
        name = canonical(key)
        if name is None:
            continue
        if not isinstance(entries, list) or not entries:
            continue
        if name not in found:
            found.append(name)
    return found


def read_registry(path: Path | str) -> tuple[str, ...]:
    """The events the registry at ``path`` registers, canonical, in file order.

    Path-addressed and strict: raises ``OSError`` if the file is unreachable and
    ``ValueError`` if it is not a registry. Never substitutes ``EVENTS``, so a
    caller reporting how many events are registered cannot accidentally report
    the default for a registry that is missing or malformed.

    Keys arrive in either engine's dialect and come back as the names in
    ``EVENTS``, deduplicated, so a file that registered an event twice under two
    spellings does not count it twice. A key this system has no event for — the
    CLI engine's ``sessionEnd``, say — registers nothing and is skipped; a
    registry where every key is like that raises, because a count of zero
    registered events is what the hook-coverage claim exists to catch.
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
    found = registered_events(hooks)
    if not found:
        raise ValueError("%s registers no event this system knows" % target)
    return tuple(found)


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
    """Our name for an event, however the engine that sent it spelled it.

    Case-insensitive and separator-insensitive, which covers every camelCase and
    snake_case variant of a name we share with the engines — ``preToolUse``,
    ``pre_tool_use``, ``PRECOMPACT``. Two Copilot CLI names are not variants of
    ours and are translated: ``userPromptSubmitted`` and ``agentStop``. Its
    ``sessionEnd`` has no KaiOS event, so it comes back ``None`` like any other
    name we do not handle, and the caller ignores it rather than dispatching it.
    """
    wanted = str(event).replace("_", "").replace("-", "").lower()
    for known in EVENTS:
        if known.lower() == wanted:
            return known
    return _ALIASES.get(wanted)
