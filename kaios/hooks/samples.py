"""One realistic sample payload per event, shared by the probe and the tests.

Rule: the probe fires the same shapes the harness sends, and every sample is
inert — no destructive command, no file path, so probing never mutates a repo.
Falsifier: a sample whose dispatch writes a file outside ``KAIOS_HOME`` or
returns a permission decision.
"""

from __future__ import annotations

SESSION = "probe-session"


def sample(event: str) -> dict:
    """The sample payload for one event name."""
    base = {"hook_event_name": event, "session_id": SESSION, "timestamp": "2026-01-01T00:00:00Z"}
    extra = _EXTRA.get(event, {})
    merged = dict(base)
    merged.update(extra)
    return merged


def samples() -> dict:
    """Every event mapped to its sample payload."""
    from . import EVENTS

    return {name: sample(name) for name in EVENTS}


_EXTRA: dict = {
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
    "Stop": {
        "stop_hook_active": False,
        "last_message": "════ KaiOS ═══════════════════════\n\nDone.\n\n\U0001f5e3️ Kai: shipped.",
    },
}
