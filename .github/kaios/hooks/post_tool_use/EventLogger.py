"""Rule: every tool call leaves one line in ``MEMORY/OBSERVABILITY/tool-events.jsonl``
with its timestamp, session, tool name, and a one-line summary.

Falsifier: a PostToolUse run that appends no line, or a line missing any of those
four fields.
"""

from __future__ import annotations

from .. import util

#: Longest summary written to the stream.
SUMMARY_LIMIT = 220


def summarize(event: dict) -> str:
    """One line describing what the call did, whatever tool it was."""
    parts: list = []
    command = util.command(event)
    if command:
        parts.append(command)
    path = util.file_path(event)
    if path:
        parts.append(path)
    if not parts:
        data = util.tool_input(event)
        if data:
            parts.append(", ".join(sorted(data)[:6]))
    result = util.tool_result(event)
    if result:
        parts.append("-> %s" % util.clip(result, 80))
    return util.clip(" ".join(parts), SUMMARY_LIMIT)


def run(event: dict, ctx) -> dict | None:
    name = util.tool_name(event) or "unknown"
    util.append_jsonl(
        ctx.paths.tool_events,
        {
            "ts": ctx.now or util.now_iso(),
            "session": ctx.session_id,
            "tool_name": name,
            "summary": summarize(event),
        },
    )
    return None
