"""Rule: every delegate dispatch is recorded to ``tool-events.jsonl`` before it runs,
so a delegate that never returns is still accounted for, and the delegate is told
to answer with raw data rather than the response format.

Falsifier: a SubagentStart run appending no line, or one whose kind is not
``subagent_start``.
"""

from __future__ import annotations

from .. import util

REMINDER = (
    "Delegate contract: return raw findings — absolute paths, commands, outputs, and what you "
    "could not verify. No banner, no closer, no response format; the orchestrator writes those."
)


def _agent(event: dict) -> str:
    for key in ("agent_name", "agentName", "subagent_type", "agent", "name", "role"):
        value = event.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return "unknown"


def run(event: dict, ctx) -> dict | None:
    util.append_jsonl(
        ctx.paths.tool_events,
        {
            "ts": ctx.now or util.now_iso(),
            "session": ctx.session_id,
            "tool_name": "subagent",
            "kind": "subagent_start",
            "agent": _agent(event),
            "summary": util.clip(util.prompt(event) or "no brief in the payload", 220),
        },
    )
    return util.context(REMINDER)
