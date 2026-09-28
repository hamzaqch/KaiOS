"""Rule: every fifth prompt in a session gets one line of voice discipline, because
register drifts slowly and nothing else in the loop notices.

Falsifier: four prompts producing a reminder, or the fifth producing none.
"""

from __future__ import annotations

from .. import state
from .. import util

#: Remind on this cadence; the counter lives in the session state file.
EVERY = 5

REMINDER = (
    "Voice check: plain words, lead with the answer, no \"not X, it's Y\", at most two closed "
    "em-dashes, nothing over a screen. Say \"verified\" or \"not verified\", never \"should work\"."
)


def run(event: dict, ctx) -> dict | None:
    count = state.bump(ctx.paths, ctx.session_id, "prompts")
    if count % EVERY != 0:
        return None
    return util.context("Prompt %d. %s" % (count, REMINDER))
