"""Rule: the same tool call with the same input, four times in a row, is a stuck
loop rather than progress, and the fourth one asks.

Falsifier: three identical calls producing an ask, or the fourth producing none.
"""

from __future__ import annotations

from .. import state
from .. import util

#: Ask on this many consecutive identical calls.
THRESHOLD = 4
_HASH_KEY = "last_tool_hash"
_COUNT_KEY = "last_tool_repeats"


def run(event: dict, ctx) -> dict | None:
    name = util.tool_name(event)
    if not name:
        return None
    digest = util.input_hash(event)
    data = state.load(ctx.paths, ctx.session_id)
    if data.get(_HASH_KEY) == digest:
        try:
            repeats = int(data.get(_COUNT_KEY) or 1) + 1
        except (TypeError, ValueError):
            repeats = 2
    else:
        repeats = 1
    data[_HASH_KEY] = digest
    data[_COUNT_KEY] = repeats
    state.save(ctx.paths, ctx.session_id, data)

    if repeats < THRESHOLD:
        return None
    return util.ask(
        "loop detected: %s called %d times in a row with identical input. Change the approach or "
        "say what is blocking." % (name, repeats)
    )
