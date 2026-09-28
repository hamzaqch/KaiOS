"""Rule: a memory problem worth knowing about — a missing directory, a stale open
ISA, an observability stream past its trim threshold — is surfaced at session
start, and a healthy memory says nothing.

Falsifier: a fixture home with a stale ISA or a missing directory producing no
line.
"""

from __future__ import annotations

from ... import memory as memory_mod
from .. import util

#: Past this, hook-events.jsonl is due for the Stop-time trim.
_BIG_STREAM = 5 * 1024 * 1024
_STALE_CAPTURE_DAYS = 30


def run(event: dict, ctx) -> dict | None:
    try:
        report = memory_mod.health(ctx.paths)
    except (OSError, ValueError):
        return None

    notes: list = []
    missing = report.get("missing_dirs") or []
    if missing:
        notes.append("%d memory directory(ies) missing" % len(missing))
    stale = report.get("stale_isas") or []
    if stale:
        notes.append(
            "%d stale open ISA(s): %s"
            % (len(stale), ", ".join(str(item.get("slug")) for item in stale[:3]))
        )
    sizes = report.get("sizes_bytes") or {}
    for name in ("hook_events", "tool_events"):
        if int(sizes.get(name) or 0) > _BIG_STREAM:
            notes.append("%s past %d MB" % (name, _BIG_STREAM // (1024 * 1024)))
    age = report.get("last_capture_age_days")
    if isinstance(age, (int, float)) and age > _STALE_CAPTURE_DAYS:
        notes.append("last capture %d day(s) old" % int(age))

    if not notes:
        return None
    return util.context("⚠️ Memory: %s." % "; ".join(notes))
