"""Rule: session state files older than seven days are deleted and the hook event
stream is trimmed to its tail once it passes five megabytes, so observability never
grows without bound.

Falsifier: an eight-day-old session file surviving a Stop, or an oversized
``hook-events.jsonl`` staying oversized.
"""

from __future__ import annotations

import time

from .. import util

#: Session state older than this is deleted.
MAX_AGE_DAYS = 7
#: Above this, the hook event stream is trimmed.
MAX_STREAM_BYTES = 5 * 1024 * 1024
#: Fraction of the stream kept when trimming.
KEEP_FRACTION = 0.5


def _prune_sessions(ctx) -> int:
    directory = ctx.paths.state
    if not directory.is_dir():
        return 0
    cutoff = time.time() - MAX_AGE_DAYS * 86400
    removed = 0
    for pattern in ("session-*.json", "precompact-*.json"):
        for candidate in sorted(directory.glob(pattern)):
            try:
                if candidate.stat().st_mtime >= cutoff:
                    continue
                candidate.unlink()
                removed += 1
            except OSError:
                continue
    return removed


def _trim_stream(path) -> bool:
    try:
        if not path.is_file() or path.stat().st_size <= MAX_STREAM_BYTES:
            return False
        raw = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    lines = raw.split("\n")
    keep = lines[-max(1, int(len(lines) * KEEP_FRACTION)) :]
    try:
        path.write_text(
            "\n".join(line for line in keep if line.strip()) + "\n", encoding="utf-8", newline="\n"
        )
    except OSError:
        return False
    return True


def run(event: dict, ctx) -> dict | None:
    removed = _prune_sessions(ctx)
    trimmed = _trim_stream(ctx.paths.hook_events)
    if not removed and not trimmed:
        return None
    parts: list = []
    if removed:
        parts.append("pruned %d stale session file(s)" % removed)
    if trimmed:
        parts.append("trimmed hook-events.jsonl")
    return util.context("🧽 Cleanup: %s." % "; ".join(parts))
