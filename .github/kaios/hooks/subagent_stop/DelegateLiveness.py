"""Rule: a delegate that returned nothing is reported as FAILED, and no claim ever
closes on a report that never arrived.

Falsifier: an empty stop payload producing no warning, or a payload with output
producing one.
"""

from __future__ import annotations

from .. import util

WARNING = (
    "delegate returned nothing: report FAILED, never close a claim on it. Re-run the delegate or "
    "do the work in this session."
)


def _agent(event: dict) -> str:
    for key in ("agent_name", "agentName", "subagent_type", "agent", "name", "role"):
        value = event.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return "unknown"


def run(event: dict, ctx) -> dict | None:
    output = util.tool_result(event)
    if not output:
        for key in ("last_message", "response", "assistant_message", "report", "summary"):
            value = event.get(key)
            if isinstance(value, str) and value.strip():
                output = value
                break
    agent = _agent(event)
    util.append_jsonl(
        ctx.paths.tool_events,
        {
            "ts": ctx.now or util.now_iso(),
            "session": ctx.session_id,
            "tool_name": "subagent",
            "kind": "subagent_stop",
            "agent": agent,
            "empty": not bool(output),
            "summary": util.clip(output or "empty output", 220),
        },
    )
    if output:
        return None
    return util.context("⚠️ %s — %s" % (agent, WARNING))
