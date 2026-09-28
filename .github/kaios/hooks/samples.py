"""One realistic sample payload per event and per dialect, for probe and tests.

Rule: the probe fires the same shapes the harness sends, in both dialects
Copilot's two hook engines speak, and every sample is inert — no destructive
command, no file path, so probing never mutates a repo.
Falsifier: a sample whose dispatch writes a file outside ``KAIOS_HOME`` or
returns a permission decision.

``claude`` is the snake_case dialect the VS Code engine sends (``tool_name``,
``tool_input``, ``session_id``). ``copilot`` is the camelCase dialect the Copilot
CLI engine sends (``toolName``, ``toolArgs``, ``sessionId``). Reading a field
under only one of those names is the bug this pair of samples exists to catch.
"""

from __future__ import annotations

from .util import BANNER, CLOSER

SESSION = "probe-session"

CLAUDE = "claude"
COPILOT = "copilot"

#: Every dialect the probe fires. Ordered: ours first, the newer engine second.
DIALECTS: tuple = (CLAUDE, COPILOT)

#: A response-shaped last message, built from the format contract's own
#: constants so a sample can never drift from the banner the gates look for.
_LAST_MESSAGE = "%s\n\nDone.\n\n%s shipped." % (BANNER, CLOSER)


def sample(event: str, dialect: str = CLAUDE) -> dict:
    """The sample payload for one event name in one dialect."""
    if dialect == COPILOT:
        base = {"sessionId": SESSION, "timestamp": "2026-01-01T00:00:00Z"}
        extra = _COPILOT.get(event, {})
    else:
        base = {
            "hook_event_name": event,
            "session_id": SESSION,
            "timestamp": "2026-01-01T00:00:00Z",
        }
        extra = _CLAUDE.get(event, {})
    merged = dict(base)
    merged.update(extra)
    return merged


def samples(dialect: str = CLAUDE) -> dict:
    """Every event mapped to its sample payload in one dialect."""
    from . import EVENTS

    return {name: sample(name, dialect) for name in EVENTS}


_CLAUDE: dict = {
    "SessionStart": {"source": "startup"},
    "UserPromptSubmit": {"prompt": "summarise what changed in the hook layer"},
    "PreToolUse": {
        "tool_name": "runCommands",
        "tool_input": {"command": "git status --porcelain"},
    },
    "PostToolUse": {
        "tool_name": "runCommands",
        "tool_input": {"command": "python -m unittest tests.test_hooks"},
        "tool_response": "OK",
    },
    "PreCompact": {"trigger": "auto"},
    "SubagentStart": {"agent_name": "Builder", "prompt": "close one claim"},
    "SubagentStop": {"agent_name": "Builder", "output": "one claim closed with evidence"},
    "Stop": {"stop_hook_active": False, "last_message": _LAST_MESSAGE},
}

_COPILOT: dict = {
    "SessionStart": {"reason": "startup"},
    "UserPromptSubmit": {"prompt": "summarise what changed in the hook layer"},
    "PreToolUse": {
        "toolName": "bash",
        "toolArgs": {"command": "git status --porcelain"},
    },
    "PostToolUse": {
        "toolName": "bash",
        "toolArgs": {"command": "python -m unittest tests.test_hooks"},
        "toolResult": "OK",
    },
    "PreCompact": {"reason": "auto"},
    "SubagentStart": {"agentName": "Builder", "prompt": "close one claim"},
    "SubagentStop": {"agentName": "Builder", "output": "one claim closed with evidence"},
    "Stop": {"stop_hook_active": False, "lastMessage": _LAST_MESSAGE},
}
