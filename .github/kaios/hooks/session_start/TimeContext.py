"""Rule: every session is told the current local date, time, weekday, and the
matching UTC stamp, so nothing reasons from a stale sense of now.

Falsifier: the injected line missing the weekday or the UTC stamp.
"""

from __future__ import annotations

from datetime import datetime, timezone

from .. import util


def run(event: dict, ctx) -> dict | None:
    try:
        local = datetime.now().astimezone()
    except (OSError, ValueError):
        local = datetime.now(timezone.utc)
    utc = datetime.now(timezone.utc)
    zone = local.tzname() or "local"
    return util.context(
        "Now: %s %s %s (%s) · %s UTC."
        % (
            local.strftime("%A"),
            local.strftime("%Y-%m-%d"),
            local.strftime("%H:%M"),
            zone,
            utc.strftime("%Y-%m-%dT%H:%MZ"),
        )
    )
