"""Rule: before a compaction, the active ISA's path and state and the session's last
tool events are written to ``MEMORY/STATE/precompact-<session>.json``, so the
session after the compaction resumes from the artifact rather than from a summary.

Falsifier: a PreCompact run leaving no snapshot file, or a snapshot without the
ISA status.
"""

from __future__ import annotations

import json

from ... import isa as isa_mod
from .. import state
from .. import util

#: How many recent tool events the snapshot carries.
TAIL = 20


def _recent_tools(ctx) -> list:
    path = ctx.paths.tool_events
    text = util.read_text(path)
    if not text:
        return []
    out: list = []
    for line in text.strip().split("\n")[-TAIL:]:
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if isinstance(record, dict):
            out.append(record)
    return out


def snapshot_path(ctx):
    return ctx.paths.state / ("precompact-%s.json" % state.sanitize(ctx.session_id))


def run(event: dict, ctx) -> dict | None:
    status = None
    if ctx.active_isa is not None:
        try:
            status = isa_mod.status(isa_mod.parse(ctx.active_isa))
        except (OSError, ValueError):
            status = None
    record = {
        "ts": ctx.now or util.now_iso(),
        "session": ctx.session_id,
        "trigger": event.get("trigger") or event.get("reason") or "unknown",
        "active_isa": str(ctx.active_isa) if ctx.active_isa is not None else None,
        "status": status,
        "tool_events": _recent_tools(ctx),
    }
    target = snapshot_path(ctx)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(record, indent=2, sort_keys=True, default=str) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    except OSError:
        return None
    return util.context(
        "state saved; resume reads the ISA. Snapshot: %s" % util.display(target, ctx.paths.home)
    )
